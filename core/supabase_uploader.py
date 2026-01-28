"""
Supabase 업로더 모듈
전처리된 PDF 데이터를 Supabase (PostgreSQL + pgvector)에 업로드
"""
import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.docstore.document import Document
import config

# 환경 변수 로드
load_dotenv(override=True)


class SupabaseUploader:
    """Supabase에 문서 데이터를 업로드하는 클래스"""
    
    def __init__(self):
        """Supabase 클라이언트와 임베딩 모델 초기화"""
        # Supabase 클라이언트 초기화
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Supabase 환경 변수가 설정되지 않았습니다.\n"
                ".env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요."
            )
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase 클라이언트 초기화 완료")
        
        # 임베딩 모델 초기화
        embedding_model = config.DEFAULT_EMBEDDING_MODEL
        embedding_kwargs = {
            "request_timeout": 600,
            "batch_size": 100,
            "max_retries": 10,
            "retry_delay": 15
        }
        # 모델이 None이 아니면 추가
        if embedding_model:
            embedding_kwargs["model"] = embedding_model
        
        self.embeddings = GoogleGenerativeAIEmbeddings(**embedding_kwargs)
        print("✅ GoogleGenerativeAIEmbeddings 초기화 완료")
    
    def upload_to_supabase(
        self,
        school_name: str,
        file_path: str,
        processed_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        전처리된 PDF 데이터를 Supabase에 업로드
        
        Args:
            school_name: 학교 이름
            file_path: PDF 파일 경로
            processed_data: 전처리된 데이터
                - toc_sections: 목차 리스트 [{"title": "...", "start_page": X, "end_page": Y}, ...]
                - chunks: LangChain Document 객체 리스트
        
        Returns:
            document_id: 생성된 문서 ID (실패 시 None)
        """
        try:
            # processed_data 검증
            if not processed_data:
                raise ValueError("processed_data가 비어있습니다.")
            
            toc_sections = processed_data.get("toc_sections", [])
            chunks = processed_data.get("chunks", [])
            
            if not chunks:
                print("⚠️  업로드할 청크가 없습니다.")
                return None
            
            filename = os.path.basename(file_path)
            
            print(f"\n📤 Supabase 업로드 시작: {school_name} - {filename}")
            print(f"   섹션 수: {len(toc_sections)}개")
            print(f"   청크 수: {len(chunks)}개")
            
            # Step 1: documents 테이블에 문서 등록
            print("\n[Step 1] documents 테이블에 문서 등록 중...")
            document_id = self._insert_document(school_name, filename, file_path)
            if not document_id:
                raise Exception("문서 등록 실패")
            print(f"   ✅ 문서 등록 완료 (ID: {document_id})")
            
            # Step 2: document_sections 테이블에 섹션 등록
            print("\n[Step 2] document_sections 테이블에 섹션 등록 중...")
            section_map = self._insert_sections(document_id, toc_sections)
            print(f"   ✅ 섹션 등록 완료 ({len(section_map)}개 섹션)")
            
            # Step 3: 임베딩 생성 (배치 처리)
            print("\n[Step 3] 임베딩 생성 중...")
            embeddings_list = self._generate_embeddings(chunks)
            print(f"   ✅ 임베딩 생성 완료 ({len(embeddings_list)}개)")
            
            # Step 4: document_chunks 테이블에 청크 등록 (배치 처리)
            print("\n[Step 4] document_chunks 테이블에 청크 등록 중...")
            chunks_inserted = self._insert_chunks(
                document_id,
                section_map,
                chunks,
                embeddings_list
            )
            print(f"   ✅ 청크 등록 완료 ({chunks_inserted}개)")
            
            print(f"\n🎉 Supabase 업로드 완료! (문서 ID: {document_id})")
            return document_id
            
        except Exception as e:
            print(f"\n❌ Supabase 업로드 중 오류 발생: {str(e)}")
            import traceback
            print(f"상세 오류:\n{traceback.format_exc()}")
            return None
    
    def _insert_document(
        self,
        school_name: str,
        filename: str,
        file_path: str
    ) -> Optional[int]:
        """
        documents 테이블에 문서 등록
        
        Args:
            school_name: 학교 이름
            filename: 파일명
            file_path: 파일 경로
        
        Returns:
            document_id: 생성된 문서 ID
        """
        try:
            # 메타데이터 구성
            metadata = {
                "file_path": file_path,
                "uploaded_at": str(os.path.getmtime(file_path)) if os.path.exists(file_path) else None
            }
            
            # documents 테이블에 삽입
            response = self.supabase.table("documents").insert({
                "school_name": school_name,
                "filename": filename,
                "metadata": metadata
            }).execute()
            
            if not response.data or len(response.data) == 0:
                raise Exception("문서 삽입 실패: 응답 데이터 없음")
            
            document_id = response.data[0]["id"]
            return document_id
            
        except Exception as e:
            print(f"   ❌ 문서 등록 오류: {str(e)}")
            return None
    
    def _insert_sections(
        self,
        document_id: int,
        toc_sections: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        document_sections 테이블에 섹션 등록
        
        Args:
            document_id: 문서 ID
            toc_sections: 목차 섹션 리스트
        
        Returns:
            section_map: {section_name: section_id} 딕셔너리
        """
        section_map = {}
        
        if not toc_sections:
            print("   ⚠️  등록할 섹션이 없습니다.")
            return section_map
        
        try:
            # 섹션 데이터 준비
            sections_data = []
            for section in toc_sections:
                section_name = section.get("title", "알 수 없음")
                page_start = section.get("start_page", 1)
                page_end = section.get("end_page", 1)
                
                sections_data.append({
                    "document_id": document_id,
                    "section_name": section_name,
                    "page_start": page_start,
                    "page_end": page_end
                })
            
            # 배치 삽입
            response = self.supabase.table("document_sections").insert(
                sections_data
            ).execute()
            
            if not response.data:
                raise Exception("섹션 삽입 실패: 응답 데이터 없음")
            
            # section_map 생성
            for section_data in response.data:
                section_name = section_data["section_name"]
                section_id = section_data["id"]
                section_map[section_name] = section_id
            
            return section_map
            
        except Exception as e:
            print(f"   ❌ 섹션 등록 오류: {str(e)}")
            return section_map
    
    def _generate_embeddings(self, chunks: List[Document]) -> List[List[float]]:
        """
        청크들의 임베딩 생성 (배치 처리)
        
        Args:
            chunks: LangChain Document 객체 리스트
        
        Returns:
            embeddings_list: 임베딩 벡터 리스트
        """
        try:
            # page_content 추출
            texts = [chunk.page_content for chunk in chunks]
            
            # 배치 임베딩 생성
            print(f"   📊 {len(texts)}개 텍스트 임베딩 생성 중...")
            embeddings_list = self.embeddings.embed_documents(texts)
            
            # 임베딩 차원 검증 (768차원)
            if embeddings_list and len(embeddings_list) > 0:
                embedding_dim = len(embeddings_list[0])
                if embedding_dim != 768:
                    print(f"   ⚠️  임베딩 차원이 예상과 다릅니다: {embedding_dim} (예상: 768)")
            
            return embeddings_list
            
        except Exception as e:
            print(f"   ❌ 임베딩 생성 오류: {str(e)}")
            raise
    
    def _insert_chunks(
        self,
        document_id: int,
        section_map: Dict[str, int],
        chunks: List[Document],
        embeddings_list: List[List[float]]
    ) -> int:
        """
        document_chunks 테이블에 청크 등록 (100개 단위 배치 처리)
        
        Args:
            document_id: 문서 ID
            section_map: {section_name: section_id} 딕셔너리
            chunks: LangChain Document 객체 리스트
            embeddings_list: 임베딩 벡터 리스트
        
        Returns:
            chunks_inserted: 삽입된 청크 수
        """
        if len(chunks) != len(embeddings_list):
            raise ValueError(
                f"청크 수({len(chunks)})와 임베딩 수({len(embeddings_list)})가 일치하지 않습니다."
            )
        
        chunks_inserted = 0
        batch_size = 100
        
        # 청크를 배치로 나누어 처리
        for batch_start in range(0, len(chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            batch_embeddings = embeddings_list[batch_start:batch_end]
            
            try:
                # 배치 데이터 준비
                chunks_data = []
                
                for idx, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                    # 섹션 ID 찾기
                    section_name = chunk.metadata.get("section_title", "알 수 없음")
                    section_id = section_map.get(section_name)
                    
                    if not section_id:
                        print(f"   ⚠️  섹션 '{section_name}'에 대한 ID를 찾을 수 없습니다. (청크 {batch_start + idx + 1})")
                        # 섹션 ID가 없으면 None으로 설정 (FK 제약 조건에 따라 실패할 수 있음)
                        # 또는 기본 섹션을 찾거나 생성해야 할 수 있음
                        continue
                    
                    # Dual Chunking 로직 적용
                    content = chunk.page_content  # 검색용 텍스트
                    raw_data = chunk.metadata.get("raw_data")  # 답변용 원본 데이터
                    
                    # raw_data가 없으면 page_content 사용
                    if not raw_data:
                        raw_data = content
                    
                    # 페이지 번호
                    page_number = chunk.metadata.get("page_number", 0)
                    
                    # 청크 타입 결정
                    chunk_type = chunk.metadata.get("chunk_type", "unknown")
                    if not chunk_type or chunk_type == "unknown":
                        # type 메타데이터로 판단
                        doc_type = chunk.metadata.get("type", "text")
                        if doc_type == "table":
                            chunk_type = "table"
                        else:
                            chunk_type = "text"
                    
                    chunks_data.append({
                        "document_id": document_id,
                        "section_id": section_id,
                        "content": content,
                        "raw_data": raw_data,
                        "embedding": embedding,  # pgvector 형식으로 자동 변환됨
                        "page_number": page_number,
                        "chunk_type": chunk_type
                    })
                
                if not chunks_data:
                    print(f"   ⚠️  배치 {batch_start // batch_size + 1}에 삽입할 데이터가 없습니다.")
                    continue
                
                # 배치 삽입
                response = self.supabase.table("document_chunks").insert(
                    chunks_data
                ).execute()
                
                if response.data:
                    chunks_inserted += len(response.data)
                    print(f"   📦 배치 {batch_start // batch_size + 1} 삽입 완료 ({len(response.data)}개)")
                else:
                    print(f"   ⚠️  배치 {batch_start // batch_size + 1} 삽입 실패: 응답 데이터 없음")
                
            except Exception as e:
                print(f"   ❌ 배치 {batch_start // batch_size + 1} 삽입 오류: {str(e)}")
                import traceback
                print(f"   상세 오류:\n{traceback.format_exc()}")
                continue
        
        return chunks_inserted


def upload_to_supabase(
    school_name: str,
    file_path: str,
    processed_data: Dict[str, Any]
) -> Optional[int]:
    """
    Supabase에 전처리된 PDF 데이터 업로드 (편의 함수)
    
    Args:
        school_name: 학교 이름
        file_path: PDF 파일 경로
        processed_data: 전처리된 데이터
            - toc_sections: 목차 리스트
            - chunks: LangChain Document 객체 리스트
    
    Returns:
        document_id: 생성된 문서 ID (실패 시 None)
    """
    uploader = SupabaseUploader()
    return uploader.upload_to_supabase(school_name, file_path, processed_data)

