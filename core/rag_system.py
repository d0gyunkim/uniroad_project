"""
RAG 시스템 모듈
질의응답 파이프라인 및 관련 섹션 선택
"""
import os
import re
from typing import List, Optional, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_teddynote.prompts import load_prompt
from langchain.docstore.document import Document
from supabase import create_client, Client
from dotenv import load_dotenv
from .searcher import SearchEngine, SupabaseSearcher
from .chunker import DocumentChunker
from .quality_evaluator import QualityEvaluator
import config

# 환경 변수 로드
load_dotenv(override=True)


class RAGSystem:
    """RAG 질의응답 시스템을 담당하는 클래스"""
    
    def __init__(self, model_name: str = None):
        """
        초기화
        
        Args:
            model_name: LLM 모델명
        """
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
        self.searcher = SearchEngine()
        self.chunker = DocumentChunker()
        self.quality_evaluator = QualityEvaluator(model_name)
        
        # Supabase 클라이언트 초기화
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            
            # 임베딩 모델 초기화
            embedding_model = config.DEFAULT_EMBEDDING_MODEL
            embedding_kwargs = {
                "request_timeout": 600,
                "batch_size": 100,
                "max_retries": 10,
                "retry_delay": 15
            }
            if embedding_model:
                embedding_kwargs["model"] = embedding_model
            
            self.embeddings = GoogleGenerativeAIEmbeddings(**embedding_kwargs)
            self.supabase_searcher = SupabaseSearcher(self.supabase, self.embeddings)
        else:
            self.supabase = None
            self.embeddings = None
            self.supabase_searcher = None
            print("⚠️  Supabase 환경 변수가 설정되지 않았습니다. 로컬 모드로 동작합니다.")
    
    def _get_relevant_sections(self, school_name: str) -> List[dict]:
        """
        Supabase에서 학교의 섹션 목록 조회
        
        Args:
            school_name: 학교 이름
            
        Returns:
            섹션 리스트 [{"id": int, "section_name": str, "page_start": int, "page_end": int}, ...]
        """
        if not self.supabase:
            raise ValueError("Supabase 클라이언트가 초기화되지 않았습니다.")
        
        try:
            # documents 테이블에서 school_name으로 문서 찾기
            documents_response = self.supabase.table("documents").select("id").eq("school_name", school_name).execute()
            
            if not documents_response.data:
                return []
            
            document_ids = [doc["id"] for doc in documents_response.data]
            
            # document_sections 테이블에서 섹션 목록 조회
            sections_response = self.supabase.table("document_sections").select(
                "id, section_name, page_start, page_end"
            ).in_("document_id", document_ids).execute()
            
            sections = []
            for section in sections_response.data:
                sections.append({
                    "id": section["id"],
                    "title": section["section_name"],
                    "start_page": section["page_start"],
                    "end_page": section["page_end"]
                })
            
            return sections
            
        except Exception as e:
            print(f"❌ Supabase 섹션 조회 중 오류: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def find_relevant_sections(self, question: str, toc_index: list = None, school_name: str = None) -> tuple:
        """
        질문과 관련된 섹션을 찾고 관련성에 따라 재순위화(re-rank)하는 메서드
        
        [작동 원리]
        1. LLM으로 질문과 관련된 섹션 선택
        2. 선택된 섹션들을 질문과의 관련성에 따라 점수화
        3. 점수 기반으로 재순위화하여 반환
        
        Args:
            question: 사용자 질문
            toc_index: 목차 인덱스 (선택, None이면 Supabase에서 조회)
            school_name: 학교 이름 (toc_index가 None일 때 필수)
            
        Returns:
            (section_numbers, thinking_process): 재순위화된 섹션 번호 리스트와 사고 과정
        """
        # toc_index가 없으면 Supabase에서 조회
        if toc_index is None:
            if not school_name:
                raise ValueError("toc_index가 None일 때는 school_name이 필수입니다.")
            toc_index = self._get_relevant_sections(school_name)
            if not toc_index:
                return ([0], "섹션을 찾을 수 없습니다.")
        
        sections_list = "\n".join([
            f"{idx+1}. {section.get('title', '알 수 없음')} (페이지 {section.get('start_page', '?')}-{section.get('end_page', '?')})"
            for idx, section in enumerate(toc_index)
        ])
        
        # 1단계: 관련 섹션 선택
        routing_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 모집요강 문서의 목차를 분석하는 전문가입니다.

사용자의 질문을 분석하고, 답변을 찾기 위해 어떤 섹션을 확인해야 할지 생각해보세요.

**사용자 질문:**
{question}

**문서의 목차 (섹션 목록):**
{sections_list}

**분석 과정:**
1. 질문의 내용을 참고하여 어떤 섹션을 확인해야 할지 생각해보세요, 단 질문의 단적인 내용 뿐만 아니라, 사용자의 의도를 파악하세요
2. 각 섹션의 제목을 보고 질문과 관련이 있는지 판단하세요,단 질문의 키워드나 단어에만 집중하지 마세요
3. 관련 섹션을 선택하고 이유를 설명하세요

**출력 형식:**
사고 과정: [질문 분석 및 섹션 선택 이유]
선택한 섹션: [섹션 번호들, 쉼표로 구분, 예: 1, 3]

---
**분석:**
""")
        
        llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0)
        chain = routing_prompt | llm | StrOutputParser()
        
        response = chain.invoke({"question": question, "sections_list": sections_list})
        
        # 사고 과정 추출
        thinking_process = ""
        if "사고 과정:" in response:
            thinking_part = response.split("사고 과정:")[1]
            if "선택한 섹션:" in thinking_part:
                thinking_process = thinking_part.split("선택한 섹션:")[0].strip()
            else:
                thinking_process = thinking_part.strip()
        
        # 섹션 번호 추출
        section_numbers = []
        if "선택한 섹션:" in response:
            section_part = response.split("선택한 섹션:")[1]
            for num_str in re.findall(r'\d+', section_part):
                num = int(num_str)
                if 1 <= num <= len(toc_index):
                    section_numbers.append(num - 1)
        else:
            for num_str in re.findall(r'\d+', response):
                num = int(num_str)
                if 1 <= num <= len(toc_index):
                    section_numbers.append(num - 1)
        
        if not section_numbers:
            section_numbers = [0]
        
        # Re-ranking 제거: Vector Search의 유사도 점수가 이미 충분히 정확하므로
        # 중복된 LLM 호출을 제거하여 응답 속도 최적화
        return section_numbers, thinking_process
    
    # _rerank_sections 메서드 제거: Re-ranking 단계를 제거하여 LLM 호출 절약 및 응답 속도 최적화
    # Vector Search의 유사도 점수가 이미 충분히 정확하므로 중복된 LLM 호출 불필요
    
    def retrieve(
        self,
        question: str,
        school_name: str,
        section_id: Optional[int] = None,
        top_k: int = None
    ) -> List[tuple]:
        """
        Supabase에서 문서 검색 수행
        
        Args:
            question: 사용자 질문
            school_name: 학교 이름 (필수)
            section_id: 섹션 ID (선택, 라우팅 결과)
            top_k: 반환할 상위 문서 수 (기본값: TOP_K_PER_SECTION)
            
        Returns:
            [(Document, score), ...] 형태의 리스트
        """
        if not self.supabase_searcher:
            raise ValueError("Supabase 검색기가 초기화되지 않았습니다.")
        
        if top_k is None:
            top_k = config.TOP_K_PER_SECTION
        
        # SupabaseSearcher로 검색 수행
        documents = self.supabase_searcher.search(
            query=question,
            school_name=school_name,
            section_id=section_id,
            top_k=top_k
        )
        
        # Document와 score를 튜플로 변환
        docs_with_scores = []
        for doc in documents:
            score = doc.metadata.get("score", 0.0)
            docs_with_scores.append((doc, score))
        
        return docs_with_scores
    
    def search_global_raw(
        self,
        school_name: str,
        query: str,
        top_k: int = 30,
        content_weight: float = 0.6,
        summary_weight: float = 0.4
    ) -> List[dict]:
        """
        라우팅 없는 전역 검색 모드
        
        섹션 선택 없이 해당 학교의 전체 문서를 대상으로 검색하고,
        요약문과 청크 간의 가중 평균 유사도 상위 10개를 반환합니다.
        
        Args:
            school_name: 학교 이름 (필수)
            query: 검색 질문 텍스트
            top_k: 초기 검색 문서 수 (기본값: 30)
            content_weight: 내용 유사도 가중치 (기본값: 0.6)
            summary_weight: Summary 유사도 가중치 (기본값: 0.4)
            
        Returns:
            [
                {
                    "chunk_id": int,
                    "section_id": int,
                    "document_id": int
                },
                ...
            ] 형태의 리스트 (상위 10개)
        """
        if not self.supabase_searcher:
            raise ValueError("Supabase 검색기가 초기화되지 않았습니다.")
        
        if not self.embeddings:
            raise ValueError("임베딩 모델이 초기화되지 않았습니다.")
        
        # 1. 라우팅 생략: 섹션 선택 없이 바로 전체 문서 검색
        print(f"🔍 전역 검색 모드: '{query}' (학교: {school_name})")
        documents = self.supabase_searcher.search(
            query=query,
            school_name=school_name,
            section_id=None,  # None으로 전달하여 전체 문서 검색
            top_k=top_k
        )
        
        if not documents:
            print("⚠️  검색 결과가 없습니다.")
            return []
        
        print(f"✅ 초기 검색 완료: {len(documents)}개 문서 발견")
        
        # 2. 각 청크의 document_id 수집
        document_ids = []
        for doc in documents:
            doc_id = doc.metadata.get("document_id")
            if doc_id:
                document_ids.append(doc_id)
        
        # 3. documents 테이블에서 summary 일괄 조회
        document_summaries = {}
        if document_ids and self.supabase:
            try:
                unique_doc_ids = list(set(document_ids))
                response = self.supabase.table("documents").select("id, summary").in_("id", unique_doc_ids).execute()
                for doc in response.data:
                    document_summaries[doc["id"]] = doc.get("summary")
            except Exception as e:
                print(f"⚠️ 문서 summary 조회 실패: {e}")
        
        # 4. 쿼리 임베딩 생성
        try:
            query_embedding = self.embeddings.embed_query(query)
        except Exception as e:
            print(f"⚠️ 쿼리 임베딩 생성 실패: {e}")
            return []
        
        # 5. 각 청크에 대해 가중 평균 유사도 계산
        import numpy as np
        
        def calculate_cosine_similarity(vec1, vec2):
            """코사인 유사도 계산"""
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot_product / (norm1 * norm2)
        
        chunks_with_weighted_scores = []
        
        for doc in documents:
            # 내용 유사도 (기존 score)
            content_similarity = doc.metadata.get("score", 0.0)
            
            # Summary 유사도 계산
            summary_similarity = 0.0
            document_id = doc.metadata.get("document_id")
            if document_id and document_id in document_summaries:
                summary = document_summaries[document_id]
                if summary:
                    try:
                        summary_embedding = self.embeddings.embed_query(summary)
                        summary_similarity = calculate_cosine_similarity(query_embedding, summary_embedding)
                    except Exception as e:
                        print(f"⚠️ Summary 유사도 계산 실패: {e}")
                        summary_similarity = 0.0
            
            # 가중 평균 계산
            weighted_average = (content_similarity * content_weight) + (summary_similarity * summary_weight)
            
            chunks_with_weighted_scores.append({
                "doc": doc,
                "weighted_score": weighted_average,
                "content_score": content_similarity,
                "summary_score": summary_similarity
            })
        
        # 6. 가중 평균 기준으로 정렬
        chunks_with_weighted_scores.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        # 7. 상위 10개 선택
        top_10_chunks = chunks_with_weighted_scores[:10]
        
        print(f"📊 가중 평균 유사도 계산 완료: 상위 10개 선택")
        
        # 8. 결과 포맷팅: 청크 id, 섹션 id, 문서 id 뿐만 아니라
        #    page_number, chunk_type, content까지 모두 포함하여 반환
        results = []
        for item in top_10_chunks:
            doc = item["doc"]
            metadata = doc.metadata
            chunk_id = metadata.get("chunk_id")
            
            if not chunk_id:
                continue
            
            results.append({
                "chunk_id": chunk_id,
                "section_id": metadata.get("section_id"),
                "document_id": metadata.get("document_id"),
                "page_number": metadata.get("page_number"),
                "chunk_type": metadata.get("chunk_type"),
                # SupabaseSearcher에서 raw_data를 page_content로 넣었으므로
                # 여기서는 그대로 content로 노출
                "content": doc.page_content,
                "score": metadata.get("score", 0.0),
            })
        
        return results
    
    def answer(
        self,
        question: str,
        school_name: str,
        conversation_history: List[tuple] = None,
        stream: bool = False,
        max_retries: int = None
    ):
        """
        전체 RAG 파이프라인 실행 (Supabase 기반)
        
        [처리 과정]
        1. 동적 라우팅: LLM으로 관련 섹션 선택
        2. Supabase 검색: 선택된 섹션에서 문서 검색
        3. 문서 병합 및 정렬
        4. Elbow Method 동적 컷오프 적용
        5. 답변 생성 (스트리밍 지원)
        
        Args:
            question: 사용자 질문
            school_name: 학교 이름 (필수)
            conversation_history: 이전 대화 히스토리 [(role, content), ...]
            stream: 스트리밍 모드 여부
            max_retries: 최대 재시도 횟수 (기본값: config.DEFAULT_MAX_RETRIES)
            
        Returns:
            stream=False: {"answer": str, "evidence": list, "selected_sections": list}
            stream=True: generator (답변 청크 스트리밍)
        """
        if not self.supabase_searcher:
            raise ValueError("Supabase 검색기가 초기화되지 않았습니다.")
        
        if max_retries is None:
            max_retries = config.DEFAULT_MAX_RETRIES
        
        # 1단계: 동적 라우팅 - 관련 섹션 선택
        section_indices, thinking_process = self.find_relevant_sections(
            question=question,
            toc_index=None,  # Supabase에서 조회
            school_name=school_name
        )
        
        # Supabase에서 섹션 목록 다시 조회 (section_id 필요)
        sections = self._get_relevant_sections(school_name)
        if not sections:
            if stream:
                yield "관련 섹션을 찾을 수 없습니다."
                return
            else:
                return {
                    "answer": "관련 섹션을 찾을 수 없습니다.",
                    "evidence": [],
                    "selected_sections": []
                }
        
        selected_sections = [sections[idx] for idx in section_indices if idx < len(sections)]
        section_ids = [section["id"] for section in selected_sections]
        
        # 2단계: 선택된 섹션별 검색 (병렬 처리 가능하지만 단순화를 위해 순차 처리)
        all_retrieved_docs_with_scores = []
        
        for section_id in section_ids:
            docs_with_scores = self.retrieve(
                question=question,
                school_name=school_name,
                section_id=section_id,
                top_k=config.TOP_K_PER_SECTION
            )
            all_retrieved_docs_with_scores.extend(docs_with_scores)
        
        # 3단계: 문서 병합 및 정렬
        retrieved_docs = self.merge_and_sort_docs(all_retrieved_docs_with_scores)
        
        # 4단계: Elbow Method 동적 컷오프 적용
        filtered_docs = self._apply_dynamic_cutoff(retrieved_docs, min_k=5, drop_threshold=0.15)
        
        if not filtered_docs:
            if stream:
                yield "관련 문서를 찾을 수 없습니다."
                return
            else:
                return {
                    "answer": "관련 문서를 찾을 수 없습니다.",
                    "evidence": [],
                    "selected_sections": selected_sections
                }
        
        # 5단계: 답변 생성
        if stream:
            # 스트리밍 모드: generator 반환
            answer_chunks = []
            for chunk in self.generate_answer(question, filtered_docs, conversation_history, stream=True):
                answer_chunks.append(chunk)
                yield chunk
            
            # 스트리밍 완료 후 메타데이터 반환은 불가능 (generator만 반환)
            return
        else:
            # 일반 모드: 전체 답변 반환
            answer = self.generate_answer(question, filtered_docs, conversation_history, stream=False)
            
            # 근거 문서 정보 수집
            evidence = []
            for doc in filtered_docs:
                evidence.append({
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "page_number": doc.metadata.get("page_number", 0),
                    "score": doc.metadata.get("score", 0.0),
                    "chunk_type": doc.metadata.get("chunk_type", "text")
                })
            
            return {
                "answer": answer,
                "evidence": evidence,
                "selected_sections": selected_sections,
                "thinking_process": thinking_process
            }
    
    def merge_and_sort_docs(self, all_retrieved_docs_with_scores: list) -> list:
        """
        검색된 문서들을 병합하고 점수 기반으로 정렬
        표 문서와 텍스트 문서를 분리하여 처리
        
        Args:
            all_retrieved_docs_with_scores: [(Document, score), ...] 리스트
            
        Returns:
            retrieved_docs: 정렬된 Document 리스트 (상위 20개)
        """
        # 1단계: 표 문서와 텍스트 문서 분리
        table_docs_with_scores = []
        text_docs_with_scores = []
        seen_tables = set()  # 표 중복 제거용
        
        for doc, score in all_retrieved_docs_with_scores:
            if doc.metadata.get('is_table', False):
                # 표 문서는 중복 제거만 수행 (문서 내용 기반)
                table_key = f"{doc.metadata.get('section_title', 'unknown')}_{hash(doc.page_content)}"
                if table_key not in seen_tables:
                    seen_tables.add(table_key)
                    table_docs_with_scores.append((doc, score))
            else:
                text_docs_with_scores.append((doc, score))
        
        # 2단계: 텍스트 문서의 연속된 청크 병합
        merged_text_docs_with_scores = []
        seen_chunks = set()
        chunks_by_section = {}
        doc_scores_map = {}
        
        for doc, score in text_docs_with_scores:
            section_key = doc.metadata.get('section_title', 'unknown')
            chunk_type = doc.metadata.get('chunk_type', 'token')
            
            # 페이지 단위 청킹인 경우 page_number를 우선 사용, 아니면 chunk_index 사용
            if chunk_type == 'page':
                chunk_identifier = doc.metadata.get('page_number', -1)
                chunk_key = f"{section_key}_page_{chunk_identifier}"
            else:
                chunk_index = doc.metadata.get('chunk_index', -1)
                chunk_key = f"{section_key}_{chunk_index}"
            
            doc_id = id(doc)
            
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                if section_key not in chunks_by_section:
                    chunks_by_section[section_key] = []
                chunks_by_section[section_key].append(doc)
                doc_scores_map[doc_id] = score
        
        # 섹션별로 연속된 청크 병합
        for section_key, section_chunks in chunks_by_section.items():
            if not section_chunks:
                continue
            
            # 청크 타입에 따라 정렬 키 선택
            first_chunk_type = section_chunks[0].metadata.get('chunk_type', 'token') if section_chunks else 'token'
            if first_chunk_type == 'page':
                # 페이지 단위 청킹: page_number로 정렬
                section_chunks.sort(key=lambda x: x.metadata.get('page_number', 0))
            else:
                # 토큰 기반 청킹: chunk_index로 정렬
                section_chunks.sort(key=lambda x: x.metadata.get('chunk_index', 0))
            
            i = 0
            while i < len(section_chunks):
                try:
                    if i >= len(section_chunks):
                        break
                    current_chunk = section_chunks[i]
                    merged_chunks = [current_chunk]
                    
                    j = i + 1
                    chunk_type = current_chunk.metadata.get('chunk_type', 'token')
                    
                    while j < len(section_chunks):
                        try:
                            if j >= len(section_chunks):
                                break
                            next_chunk = section_chunks[j]
                            
                            # 청크 타입에 따라 연속성 확인
                            if chunk_type == 'page':
                                # 페이지 단위 청킹: page_number가 연속인지 확인
                                current_page = current_chunk.metadata.get('page_number', -1)
                                next_page = next_chunk.metadata.get('page_number', -1)
                                is_consecutive = current_page >= 0 and next_page == current_page + 1
                            else:
                                # 토큰 기반 청킹: chunk_index가 연속인지 확인
                                current_index = current_chunk.metadata.get('chunk_index', -1)
                                next_index = next_chunk.metadata.get('chunk_index', -1)
                                is_consecutive = current_index >= 0 and next_index == current_index + 1
                            
                            if is_consecutive:
                                merged_chunks.append(next_chunk)
                                current_chunk = next_chunk
                                j += 1
                            else:
                                break
                        except (IndexError, KeyError, TypeError) as e:
                            print(f"⚠️  청크 병합 중 오류 (j={j}): {e}")
                            break
                    
                    # 연속된 청크가 여러 개인 경우 병합
                    if len(merged_chunks) > 1:
                        chunk_type = merged_chunks[0].metadata.get('chunk_type', 'token') if merged_chunks else 'token'
                        max_score = 0
                        
                        # 페이지 단위 청킹인 경우 단순 연결, 토큰 기반은 overlap 병합
                        if chunk_type == 'page':
                            # 페이지 단위: 단순히 내용을 연결 (overlap 없음)
                            merged_content = "\n\n".join([
                                chunk.page_content if hasattr(chunk, 'page_content') else str(chunk)
                                for chunk in merged_chunks
                            ])
                            
                            # 점수 계산
                            for chunk_doc in merged_chunks:
                                doc_id = id(chunk_doc)
                                if doc_id in doc_scores_map:
                                    max_score = max(max_score, doc_scores_map[doc_id])
                            
                            if merged_chunks and len(merged_chunks) > 0:
                                merged_doc = Document(
                                    page_content=merged_content,
                                    metadata=merged_chunks[0].metadata.copy() if hasattr(merged_chunks[0], 'metadata') else {}
                                )
                                # 페이지 범위 정보 추가
                                page_numbers = [chunk.metadata.get('page_number', 0) for chunk in merged_chunks if chunk.metadata.get('page_number', 0) > 0]
                                if page_numbers:
                                    merged_doc.metadata['page_range'] = f"{min(page_numbers)}-{max(page_numbers)}"
                                merged_doc.metadata['merged_chunks'] = len(merged_chunks)
                                merged_text_docs_with_scores.append((merged_doc, max_score))
                        else:
                            # 토큰 기반: overlap 정보를 사용한 병합
                            chunk_data = []
                            
                            for chunk_doc in merged_chunks:
                                try:
                                    chunk_data.append({
                                        "content": chunk_doc.page_content if hasattr(chunk_doc, 'page_content') else str(chunk_doc),
                                        "start_pos": chunk_doc.metadata.get('chunk_start_pos', 0) if hasattr(chunk_doc, 'metadata') else 0,
                                        "end_pos": chunk_doc.metadata.get('chunk_end_pos', 0) if hasattr(chunk_doc, 'metadata') else 0,
                                        "overlap_prev": {
                                            "text": chunk_doc.metadata.get('overlap_prev_text', '') if hasattr(chunk_doc, 'metadata') else '',
                                            "start": chunk_doc.metadata.get('overlap_prev_start', 0) if hasattr(chunk_doc, 'metadata') else 0,
                                            "end": chunk_doc.metadata.get('overlap_prev_end', 0) if hasattr(chunk_doc, 'metadata') else 0
                                        },
                                        "overlap_next": {
                                            "text": chunk_doc.metadata.get('overlap_next_text', '') if hasattr(chunk_doc, 'metadata') else '',
                                            "start": chunk_doc.metadata.get('overlap_next_start', 0) if hasattr(chunk_doc, 'metadata') else 0,
                                            "end": chunk_doc.metadata.get('overlap_next_end', 0) if hasattr(chunk_doc, 'metadata') else 0
                                        }
                                    })
                                    doc_id = id(chunk_doc)
                                    if doc_id in doc_scores_map:
                                        max_score = max(max_score, doc_scores_map[doc_id])
                                except (AttributeError, KeyError, TypeError) as e:
                                    print(f"⚠️  청크 데이터 생성 중 오류: {e}")
                                    continue
                            
                            if chunk_data:
                                try:
                                    merged_content = self.chunker.merge_chunks_with_overlap(chunk_data)
                                    if merged_chunks and len(merged_chunks) > 0:
                                        merged_doc = Document(
                                            page_content=merged_content,
                                            metadata=merged_chunks[0].metadata.copy() if hasattr(merged_chunks[0], 'metadata') else {}
                                        )
                                        merged_doc.metadata['merged_chunks'] = len(merged_chunks)
                                        merged_text_docs_with_scores.append((merged_doc, max_score))
                                except Exception as e:
                                    print(f"⚠️  청크 병합 중 오류: {e}")
                                    # 병합 실패 시 첫 번째 청크만 추가
                                    if merged_chunks and len(merged_chunks) > 0:
                                        try:
                                            doc_id = id(merged_chunks[0])
                                            score = doc_scores_map.get(doc_id, 0)
                                            merged_text_docs_with_scores.append((merged_chunks[0], score))
                                        except:
                                            pass
                    else:
                        # 병합할 청크가 없으면 그대로 추가
                        if merged_chunks and len(merged_chunks) > 0:
                            try:
                                doc_id = id(merged_chunks[0])
                                score = doc_scores_map.get(doc_id, 0)
                                merged_text_docs_with_scores.append((merged_chunks[0], score))
                            except (IndexError, KeyError, TypeError) as e:
                                print(f"⚠️  청크 추가 중 오류: {e}")
                    
                    i = j
                except (IndexError, KeyError, TypeError) as e:
                    print(f"⚠️  섹션 청크 처리 중 오류 (i={i}): {e}")
                    i += 1  # 오류 발생 시 다음으로 이동
        
        # 3단계: 표 문서와 텍스트 문서 통합 후 점수로 정렬
        all_docs_with_scores = table_docs_with_scores + merged_text_docs_with_scores
        all_docs_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 TOP_K_FINAL개 선택
        retrieved_docs_with_scores = all_docs_with_scores[:config.TOP_K_FINAL]
        
        # 점수 정보를 메타데이터에 저장 (동적 컷오프를 위해)
        for doc, score in retrieved_docs_with_scores:
            doc.metadata['similarity_score'] = score
        
        return [doc for doc, score in retrieved_docs_with_scores]
    
    # 표 분석 단계 제거: 별도 LLM 호출을 제거하고 raw_data를 직접 컨텍스트에 포함하여
    # (표 분석 호출 + 답변 생성 호출) -> (단일 답변 생성 호출)로 통합하여 속도 2배 향상
    
    def _apply_dynamic_cutoff(self, retrieved_docs: list, min_k: int = 5, drop_threshold: float = 0.15) -> list:
        """
        Elbow Method 기반 동적 컷오프 적용
        
        [원리]
        - 상위 min_k개는 무조건 유지 (안전장치)
        - 그 이후 문서부터 점수 차이를 계산
        - 점수 차이가 drop_threshold 이상 벌어지면 그 이후 문서 제거
        - 관련성이 낮은 문서 제거로 TTFT 향상 및 할루시네이션 방지
        
        Args:
            retrieved_docs: 검색된 문서 리스트 (similarity_score 메타데이터 포함)
            min_k: 최소 유지 개수 (기본값: 5)
            drop_threshold: 점수 급락 임계값 (기본값: 0.15)
            
        Returns:
            filtered_docs: 필터링된 문서 리스트
        """
        if not retrieved_docs:
            return []
        
        # 점수 기반으로 정렬 확인 (이미 정렬되어 있어야 함)
        docs_with_scores = []
        for doc in retrieved_docs:
            score = doc.metadata.get('similarity_score', 0.0)
            docs_with_scores.append((doc, score))
        
        # 점수 내림차순 정렬 (혹시 모를 경우를 대비)
        docs_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        original_count = len(docs_with_scores)
        
        # 상위 min_k개는 무조건 유지
        if len(docs_with_scores) <= min_k:
            # 문서 수가 min_k 이하면 모두 유지
            filtered_docs = [doc for doc, score in docs_with_scores]
            print(f"📊 동적 컷오프: {original_count}개 문서 → {len(filtered_docs)}개 유지 (min_k={min_k} 이하)")
            return filtered_docs
        
        # min_k개 이후부터 점수 차이 확인
        kept_docs = docs_with_scores[:min_k]  # 상위 min_k개는 무조건 유지
        
        for i in range(min_k, len(docs_with_scores) - 1):
            current_doc, current_score = docs_with_scores[i]
            next_doc, next_score = docs_with_scores[i + 1]
            
            # 점수 차이 계산
            score_drop = current_score - next_score
            
            # 점수 차이가 임계값 이상이면 여기서 컷오프
            if score_drop >= drop_threshold:
                print(f"📊 동적 컷오프: {original_count}개 문서 → {len(kept_docs)}개 유지 (인덱스 {i}에서 {score_drop:.3f} 점수 차이 감지)")
                break
            
            # 점수 차이가 임계값 미만이면 유지
            kept_docs.append((current_doc, current_score))
        else:
            # 마지막 문서까지 임계값 미만이면 마지막 문서도 유지
            if len(docs_with_scores) > min_k:
                kept_docs.append(docs_with_scores[-1])
            print(f"📊 동적 컷오프: {original_count}개 문서 → {len(kept_docs)}개 유지 (임계값 미만으로 모두 유지)")
        
        # Document만 반환 (점수는 메타데이터에 이미 저장됨)
        filtered_docs = [doc for doc, score in kept_docs]
        
        return filtered_docs
    
    def generate_answer(self, question: str, retrieved_docs: list, conversation_history: list = None, stream: bool = False):
        """
        검색된 문서를 기반으로 답변 생성 (대화 연속성 고려, 스트리밍 지원)
        표는 별도 분석 없이 raw_data를 직접 컨텍스트에 포함하여 속도 최적화

        Args:
            question: 사용자 질문
            retrieved_docs: 검색된 문서 리스트 또는 [(Document, score), ...] 튜플 리스트
            conversation_history: 이전 대화 히스토리 [(role, content), ...]
            stream: 스트리밍 모드 여부 (True면 generator 반환, False면 문자열 반환)

        Returns:
            answer: 생성된 답변 (stream=False일 때) 또는 generator (stream=True일 때)
        """
        if not retrieved_docs:
            if stream:
                yield "관련 문서를 찾을 수 없습니다."
                return
            else:
                return "관련 문서를 찾을 수 없습니다."

        # retrieved_docs가 튜플 리스트인지 확인하고 Document 리스트로 변환
        if retrieved_docs and isinstance(retrieved_docs[0], tuple):
            # [(Document, score), ...] 형태인 경우 Document 리스트로 변환
            docs_list = []
            for doc, score in retrieved_docs:
                # 점수를 메타데이터에 저장
                doc.metadata['similarity_score'] = score
                docs_list.append(doc)
            retrieved_docs = docs_list

        # Elbow Method 기반 동적 컷오프 적용 (TTFT 향상 및 노이즈 제거)
        filtered_docs = self._apply_dynamic_cutoff(retrieved_docs, min_k=5, drop_threshold=0.15)
        
        # 필터링된 문서로 컨텍스트 구성
        # 표와 텍스트 분리
        table_docs = [doc for doc in filtered_docs if doc.metadata.get('is_table', False)]
        text_docs = [doc for doc in filtered_docs if not doc.metadata.get('is_table', False)]
        
        # 컨텍스트 구성 (Dual Chunking 전략: 표는 raw_data 직접 사용, 별도 분석 제거)
        context_parts = []
        doc_counter = 1  # 전체 문서 번호 (표와 텍스트 통합)
        
        # 1. 텍스트 문서 추가
        for doc in text_docs:
            section_info = ""
            if 'section_title' in doc.metadata:
                section_info = f"[{doc.metadata['section_title']}] "
            
            # 병합된 청크 정보 추가
            merged_info = ""
            if doc.metadata.get('merged_chunks', 0) > 1:
                merged_info = f" [병합된 {doc.metadata['merged_chunks']}개 청크]"
            
            context_parts.append(f"문서 {doc_counter}. {section_info}{merged_info}\n{doc.page_content}\n")
            doc_counter += 1
        
        # 2. 표 문서 추가 (Dual Chunking: raw_data를 직접 컨텍스트에 포함)
        # 별도 LLM 호출 없이 원본 표 데이터를 그대로 사용하여 속도 최적화
        for table_doc in table_docs:
            section_info = ""
            if 'section_title' in table_doc.metadata:
                section_info = f"[{table_doc.metadata['section_title']}] "
            
            # Context Swap: raw_data를 직접 사용 (표 분석 단계 제거)
            raw_data = table_doc.metadata.get('raw_data', None)
            if raw_data:
                context_parts.append(
                    f"문서 {doc_counter}. {section_info}[표 데이터 - 원본 마크다운]\n"
                    f"{raw_data}\n"
                )
            else:
                # raw_data가 없는 경우 (레거시 호환성: summary 사용)
                context_parts.append(
                    f"문서 {doc_counter}. {section_info}[표 데이터 - 요약]\n"
                    f"{table_doc.page_content}\n"
                )
            doc_counter += 1
        
        context = "\n---\n".join(context_parts)
        
        # 대화 히스토리 포맷팅
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_parts = []
            # 최근 6개 대화만 포함 (너무 길어지지 않도록)
            recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            for role, content in recent_history:
                if role == "user":
                    history_parts.append(f"학생: {content}")
                elif role == "assistant":
                    history_parts.append(f"컨설턴트: {content}")
            
            if history_parts:
                history_text = "\n\n**이전 대화 맥락:**\n" + "\n".join(history_parts) + "\n"
        
        prompt = load_prompt("prompts/pdf-rag.yaml", encoding="utf-8")
        llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0, streaming=stream)
        chain = prompt | llm | StrOutputParser()
        
        if stream:
            # 스트리밍 모드: generator 반환
            for chunk in chain.stream({
                "context": context, 
                "question": question,
                "conversation_history": history_text
            }):
                yield chunk
        else:
            # 일반 모드: 문자열 반환
            answer = chain.invoke({
                "context": context, 
                "question": question,
                "conversation_history": history_text
            })
            return answer

