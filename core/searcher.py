"""
검색 엔진 모듈
단순 벡터 기반 유사도 검색 기능 및 Supabase 기반 검색
"""
from langchain.docstore.document import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase import Client
from typing import List, Optional
import config


class SearchEngine:
    """벡터 기반 유사도 검색을 담당하는 클래스"""
    
    def __init__(self):
        """
        초기화
        """
        pass
    
    def hybrid_search(
        self,
        question: str,
        vectorstore,
        documents: list,
        top_k: int = 10
    ) -> list:
        """
        단순 벡터 기반 유사도 검색
        
        Args:
            question: 사용자 질문
            vectorstore: FAISS 벡터스토어
            documents: 문서 리스트 (사용하지 않음, 호환성을 위해 유지)
            top_k: 반환할 상위 문서 수
            
        Returns:
            [(Document, score), ...] 형태의 리스트
        """
        # 단순 벡터 검색으로 많이 가져오기
        try:
            # similarity_search_with_score로 점수와 함께 검색
            vector_results = vectorstore.similarity_search_with_score(question, k=top_k)
            
            # 거리 점수를 유사도 점수로 변환 (거리가 작을수록 유사도 높음)
            # FAISS는 L2 거리를 반환하므로, 1 / (1 + distance)로 변환
            vector_docs_with_scores = [
                (doc, 1.0 / (1.0 + score))  # 거리를 유사도로 변환
                for doc, score in vector_results
            ]
        except Exception as e:
            # 오류 발생 시 빈 리스트 반환
            vector_docs_with_scores = []
        
        return vector_docs_with_scores


class SupabaseSearcher:
    """Supabase 기반 벡터 검색을 담당하는 클래스"""
    
    def __init__(self, supabase_client: Client, embeddings: GoogleGenerativeAIEmbeddings):
        """
        초기화
        
        Args:
            supabase_client: Supabase 클라이언트
            embeddings: 임베딩 모델
        """
        self.supabase = supabase_client
        self.embeddings = embeddings
    
    def search(
        self,
        query: str,
        school_name: str,
        section_id: Optional[int] = None,
        top_k: int = 30
    ) -> List[Document]:
        """
        Supabase에서 벡터 유사도 검색 수행
        
        Args:
            query: 검색 질문 텍스트
            school_name: 학교 이름 (필수)
            section_id: 섹션 ID (선택, 라우팅 결과)
            top_k: 반환할 상위 문서 수
            
        Returns:
            Document 객체 리스트 (Context Swap 적용: page_content에 raw_data 사용)
        """
        try:
            # 1. query를 임베딩 벡터로 변환
            query_embedding = self.embeddings.embed_query(query)
            
            # 2. Supabase RPC 함수 호출
            # Supabase 함수 인자 이름에 맞춰 파라미터 구성
            rpc_params = {
                "filter_school_name": school_name,
                "filter_section_id": section_id,
                "match_count": top_k,
                "match_threshold": 0.0,  # 모든 결과 반환 (점수로 필터링)
                "query_embedding": query_embedding,
            }
            
            # section_id가 제공된 경우 필터 추가, None이면 전체 문서 검색
            if section_id is not None:
                rpc_params["filter_section_id"] = section_id
            # section_id가 None이면 filter_section_id를 포함하지 않아 전체 문서 검색
            
            # RPC 함수 호출
            response = self.supabase.rpc(
                "match_document_chunks",
                rpc_params
            ).execute()
            
            if not response.data:
                return []
            
            # 3. 결과를 LangChain Document 객체로 변환 (Context Swap 적용)
            documents = []
            for row in response.data:
                # Context Swap: page_content에 raw_data 사용 (원본 데이터)
                page_content = row.get("raw_data") or row.get("content", "")
                
                # 메타데이터 구성
                document_id = row.get("document_id")
                
                # 디버깅: document_id가 없으면 첫 번째 행의 키를 출력
                if not document_id and len(documents) == 0:
                    print(f"⚠️ RPC 응답에 document_id가 없습니다. 사용 가능한 키: {list(row.keys())}")
                
                metadata = {
                    "page_number": row.get("page_number", 0),
                    "score": row.get("similarity", 0.0),  # 유사도 점수
                    "chunk_type": row.get("chunk_type", "text"),
                    "section_id": row.get("section_id"),
                    "document_id": document_id,  # None이어도 포함
                    "chunk_id": row.get("id")
                }
                
                # section_name이 있으면 section_title로도 추가 (기존 코드 호환성)
                section_name = row.get("section_name")
                if section_name:
                    metadata["section_title"] = section_name
                
                # chunk_type에 따라 추가 메타데이터 설정
                if row.get("chunk_type") == "table":
                    metadata["is_table"] = True
                    # 표의 경우 raw_data가 있으면 사용
                    if row.get("raw_data"):
                        metadata["raw_data"] = row.get("raw_data")
                else:
                    metadata["is_table"] = False
                
                # Document 객체 생성
                doc = Document(
                    page_content=page_content,
                    metadata=metadata
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            print(f"❌ Supabase 검색 중 오류: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []

