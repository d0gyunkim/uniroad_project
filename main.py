"""
목차 기반 동적 라우팅 RAG 시스템 - 메인 실행 파일
Streamlit 앱 진입점
"""
import streamlit as st
from langchain_core.messages.chat import ChatMessage
from langchain_teddynote import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import os

from core import (
    TOCProcessor,
    SectionPreprocessor,
    RAGSystem,
    SearchEngine
)
import config

# 프로젝트 이름 설정
logging.langsmith("[Project] TOC-Based Dynamic Routing RAG - Gemini")

# Streamlit 페이지 설정
st.title("📑 목차 기반 동적 라우팅 입시 컨설턴트")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "toc_index" not in st.session_state:
    st.session_state["toc_index"] = None

if "pdf_path" not in st.session_state:
    st.session_state["pdf_path"] = None

if "section_cache" not in st.session_state:
    st.session_state["section_cache"] = {}

if "section_vectorstores" not in st.session_state:
    st.session_state["section_vectorstores"] = {}

# 사이드바
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    
    uploaded_file = st.file_uploader("원본 PDF 업로드", type=["pdf"])
    
    selected_model = config.DEFAULT_LLM_MODEL
    
    max_retries = st.slider("최대 재시도 횟수", min_value=1, max_value=5, value=config.DEFAULT_MAX_RETRIES)
    
    st.markdown("---")
    st.markdown("### 🧪 테스트 모드")
    extract_only_mode = st.checkbox(
        "원본 정보만 추출 (LLM 답변 생성 없음)",
        value=False,
        help="체크하면 검색된 문서의 원본 정보만 추출하여 표시합니다. LLM 기반 답변 생성은 건너뜁니다."
    )
    clean_extract_mode = st.checkbox(
        "순수 정보만 출력 (메타데이터 제외)",
        value=False,
        help="체크하면 메타데이터나 추가 정보 없이 쿼리에 적절한 정보만 깔끔하게 출력합니다."
    )
    
    st.markdown("---")
    st.markdown("### 📑 목차 기반 동적 라우팅")
    st.markdown("1. 원본 PDF 업로드")
    st.markdown("2. 목차 자동 감지 및 파싱")
    st.markdown("3. 쿼리별 관련 섹션 자동 선택")
    st.markdown("4. 해당 섹션만 동적 처리")
    st.markdown("5. **표 별도 분석 및 요약**")
    st.markdown("6. **품질 평가 및 재시도**")
    st.markdown("")
    st.markdown("✅ 사전 분할 불필요")
    st.markdown("✅ 동적 섹션 선택")
    st.markdown("✅ 표 구조 인식 및 요약")
    st.markdown("✅ 효율적 처리")
    
    st.markdown("---")
    st.markdown("### ⚙️ 시스템 상태")
    if st.session_state["toc_index"]:
        st.success(f"✅ 목차 인덱스 로드 완료")
        st.info(f"📄 섹션 수: {len(st.session_state['toc_index'])}개")
        with st.expander("📋 목차 보기"):
            for section in st.session_state["toc_index"]:
                st.markdown(f"**{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
    else:
        st.warning("⏳ PDF 업로드 대기 중")


def print_messages():
    """이전 대화 기록 출력"""
    for chat_message in st.session_state["messages"]:
        st.chat_message(chat_message.role).write(chat_message.content)


def add_message(role, message):
    """새로운 메시지 추가"""
    st.session_state["messages"].append(ChatMessage(role=role, content=message))


@st.cache_resource(show_spinner="PDF 전처리 중... (목차 분석, 표 인식, 임베딩 생성)")
def build_toc_index_and_preprocess(pdf_path, _cache_key, _file_mtime):
    """
    목차 인덱스 생성 및 모든 섹션 전처리
    
    Args:
        pdf_path: PDF 파일 경로
        _cache_key: 캐시 키 (파일명)
        _file_mtime: 파일 수정 시간 (캐시 무효화용)
        
    Returns:
        {
            "sections": 섹션 리스트,
            "section_data": 섹션별 전처리 결과
        }
    """
    toc_processor = TOCProcessor(selected_model)
    preprocessor = SectionPreprocessor(selected_model)
    
    # 1단계: 목차 페이지 감지
    st.info("🔍 목차 페이지 감지 중...")
    toc_pages = toc_processor.detect_toc_pages(pdf_path)
    
    if not toc_pages:
        st.warning("⚠️ 목차 페이지를 찾을 수 없습니다. 페이지 수 기반 분할을 사용합니다.")
        sections = toc_processor.create_default_sections(pdf_path)
    else:
        st.success(f"✅ 목차 페이지 발견: {[p+1 for p in toc_pages]}")
        
        # 2단계: 목차 구조 파싱
        st.info("📋 목차 구조 파싱 중...")
        sections = toc_processor.parse_toc_structure(pdf_path, toc_pages)
        
        if not sections:
            st.warning("⚠️ 목차 파싱 실패. 페이지 수 기반 분할을 사용합니다.")
            sections = toc_processor.create_default_sections(pdf_path)
    
    # 3단계: 페이지 범위 검증
    sections = toc_processor.validate_and_fix_sections(sections, pdf_path)
    st.success(f"✅ {len(sections)}개 섹션 추출 완료")
    
    # 4단계: 병렬 전처리
    st.info(f"📄 {len(sections)}개 섹션 병렬 전처리 중... (표 구조 인식 및 임베딩 생성)")
    
    section_data = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def process_section(section):
        """섹션 전처리 함수 (병렬 실행용)"""
        section_key = f"{section['start_page']}_{section['end_page']}"
        result = preprocessor.preprocess_section(section, pdf_path)
        return {
            "section_key": section_key,
            "result": result,
            "section": section
        }
    
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_section = {
            executor.submit(process_section, section): idx
            for idx, section in enumerate(sections, 1)
        }
        
        completed = 0
        total = len(sections)
        
        for future in as_completed(future_to_section):
            idx = future_to_section[future]
            try:
                data = future.result()
                
                # data가 None이거나 필수 키가 없으면 건너뛰기
                if not data:
                    st.error(f"❌ 섹션 {idx} 처리 중 오류: 결과가 None입니다")
                    continue
                    
                section_key = data.get("section_key", f"section_{idx}")
                result = data.get("result", {})
                section = data.get("section", {"title": f"섹션 {idx}"})
                
                # result가 None이거나 필수 키가 없으면 기본값 사용
                if not result:
                    result = {
                        "vectorstore": None,
                        "documents": [],
                        "table_count": 0
                    }
                
                section_data[section_key] = {
                    "vectorstore": result.get("vectorstore"),
                    "documents": result.get("documents", []),
                    "section": section,
                    "table_count": result.get("table_count", 0)
                }
                
                completed += 1
                progress = completed / total
                progress_bar.progress(progress)
                
                table_count = result.get("table_count", 0)
                table_info = f" (표 {table_count}개)" if table_count > 0 else ""
                section_title = section.get("title", f"섹션 {idx}")
                status_text.text(f"✅ {completed}/{total} 완료: '{section_title}'{table_info}")
                st.success(f"✅ 섹션 {idx} 완료: '{section_title}'{table_info}")
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ 섹션 {idx} 처리 중 상세 오류:\n{error_details}")
                st.error(f"❌ 섹션 {idx} 처리 중 오류 발생: {str(e)}")
                # 오류 발생해도 계속 진행
                completed += 1
                progress = completed / total
                progress_bar.progress(progress)
    
    progress_bar.empty()
    status_text.empty()
    st.success(f"🎉 모든 섹션 전처리 완료! ({len(sections)}개)")
    
    return {
        "sections": sections,
        "section_data": section_data
    }


def extract_clean_information(retrieved_docs, question):
    """
    검색된 문서들의 순수 정보만 추출 (메타데이터 제외, Elbow Method 기반 동적 컷오프 적용)
    
    Args:
        retrieved_docs: Document 리스트 (similarity_score가 메타데이터에 포함됨)
        question: 사용자 질문
        
    Returns:
        포맷팅된 순수 정보 문자열 (메타데이터 없음)
    """
    if not retrieved_docs:
        return "검색된 문서가 없습니다."
    
    # Elbow Method 기반 동적 컷오프 적용
    from core.rag_system import RAGSystem
    rag_system = RAGSystem()
    filtered_docs = rag_system._apply_dynamic_cutoff(retrieved_docs)
    
    if not filtered_docs:
        return "동적 컷오프 적용 후 관련 문서를 찾을 수 없습니다."
    
    # 순수 정보만 추출 (메타데이터 없이)
    output_parts = []
    
    for doc in filtered_docs:
        # 원본 내용만 추출
        if doc.metadata.get('is_table', False) and doc.metadata.get('raw_data'):
            # 표의 경우 raw_data 사용
            output_parts.append(doc.metadata['raw_data'])
        else:
            # 텍스트의 경우 page_content 사용
            output_parts.append(doc.page_content)
        
        # 문서 간 구분
        output_parts.append("\n\n---\n\n")
    
    return "".join(output_parts).strip()


def extract_raw_information(retrieved_docs, question):
    """
    검색된 문서들의 원본 정보만 추출하여 포맷팅 (Elbow Method 기반 동적 컷오프 적용)
    
    Args:
        retrieved_docs: Document 리스트 (similarity_score가 메타데이터에 포함됨)
        question: 사용자 질문
        
    Returns:
        포맷팅된 원본 정보 문자열
    """
    if not retrieved_docs:
        return "검색된 문서가 없습니다."
    
    # 동적 컷오프 적용 전 문서 수
    original_count = len(retrieved_docs)
    
    # Elbow Method 기반 동적 컷오프 적용 (rag_system의 메서드 사용)
    from core.rag_system import RAGSystem
    rag_system = RAGSystem()
    filtered_docs = rag_system._apply_dynamic_cutoff(retrieved_docs)
    
    if not filtered_docs:
        return "동적 컷오프 적용 후 관련 문서를 찾을 수 없습니다."
    
    # 컷오프 적용 후 문서 수
    filtered_count = len(filtered_docs)
    
    # 포맷팅된 정보 생성
    output_parts = []
    output_parts.append(f"## 📋 질문: {question}\n")
    output_parts.append(f"**검색된 문서 수:** {original_count}개 → **컷오프 적용 후:** {filtered_count}개\n")
    if original_count > filtered_count:
        removed_count = original_count - filtered_count
        output_parts.append(f"*✂️ Elbow Method 기반 동적 컷오프로 관련성 낮은 문서 {removed_count}개 제거됨*\n")
    output_parts.append("---\n")
    
    # 섹션별로 그룹화 (컷오프 적용된 문서만)
    docs_by_section = {}
    for doc in filtered_docs:
        section_title = doc.metadata.get('section_title', '알 수 없음')
        if section_title not in docs_by_section:
            docs_by_section[section_title] = []
        docs_by_section[section_title].append(doc)
    
    doc_counter = 1
    for section_title, docs in sorted(docs_by_section.items()):
        output_parts.append(f"### 📑 섹션: {section_title}\n")
        output_parts.append(f"**문서 수:** {len(docs)}개\n\n")
        
        for doc in docs:
            # 메타데이터 정보 수집
            metadata_info = []
            is_table = doc.metadata.get('is_table', False)
            chunk_type = doc.metadata.get('chunk_type', 'token')
            
            # 페이지 정보
            if chunk_type == 'page':
                page_number = doc.metadata.get('page_number', 0)
                page_range = doc.metadata.get('page_range', None)
                if page_range:
                    metadata_info.append(f"📄 페이지 {page_range}")
                elif page_number > 0:
                    metadata_info.append(f"📄 페이지 {page_number}")
            else:
                if 'section_start' in doc.metadata and 'section_end' in doc.metadata:
                    metadata_info.append(f"📄 페이지 {doc.metadata['section_start']}-{doc.metadata['section_end']}")
            
            # 표 여부
            if is_table:
                metadata_info.append("📊 표 데이터")
            
            # 병합 정보
            if doc.metadata.get('merged_chunks', 0) > 1:
                merged_count = doc.metadata['merged_chunks']
                if chunk_type == 'page':
                    metadata_info.append(f"🔗 {merged_count}개 페이지 병합")
                else:
                    metadata_info.append(f"🔗 {merged_count}개 청크 병합")
            
            # 유사도 점수
            similarity_score = doc.metadata.get('similarity_score', 0)
            if similarity_score > 0:
                metadata_info.append(f"⭐ 관련성: {similarity_score:.3f}")
            
            output_parts.append(f"#### 문서 {doc_counter}\n")
            if metadata_info:
                output_parts.append(f"**정보:** {' | '.join(metadata_info)}\n\n")
            
            # 원본 내용 추출
            if is_table and doc.metadata.get('raw_data'):
                # 표의 경우 raw_data 사용
                output_parts.append("**원본 표 데이터:**\n")
                output_parts.append("```markdown\n")
                output_parts.append(doc.metadata['raw_data'])
                output_parts.append("\n```\n")
                
                # 요약도 함께 표시
                if doc.page_content and doc.page_content.strip():
                    output_parts.append("\n**표 요약:**\n")
                    output_parts.append(f"{doc.page_content}\n")
            else:
                # 텍스트의 경우 page_content 사용
                output_parts.append("**원본 내용:**\n")
                output_parts.append("```\n")
                output_parts.append(doc.page_content)
                output_parts.append("\n```\n")
            
            output_parts.append("\n---\n\n")
            doc_counter += 1
    
    return "".join(output_parts)


def query_with_retry(question, pdf_path, toc_index, max_retries=3, extract_only=False, clean_extract=False):
    """
    질의응답 수행 (재시도 포함)
    
    Args:
        question: 사용자 질문
        pdf_path: PDF 파일 경로
        toc_index: 목차 인덱스
        max_retries: 최대 재시도 횟수
        extract_only: True면 원본 정보만 추출, False면 LLM 답변 생성
        clean_extract: True면 메타데이터 없이 순수 정보만 출력
        
    Returns:
        {
            "answer": 답변 또는 원본 정보,
            "evidence": 근거 문서 리스트,
            "selected_sections": 선택된 섹션 리스트
        }
    """
    rag_system = RAGSystem(selected_model)
    searcher = SearchEngine()
    
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            st.warning(f"🔄 {attempt}번째 시도 중... (이전 답변 품질 개선 필요)")
        
        # 1단계: 관련 섹션 찾기
        st.info(f"🤔 질문 분석 및 관련 섹션 탐색 중... (시도 {attempt}/{max_retries})")
        section_indices, thinking_process = rag_system.find_relevant_sections(question, toc_index)
        
        selected_sections = [toc_index[idx] for idx in section_indices]
        
        with st.expander(f"🧠 질문 분석 및 섹션 선택 (시도 {attempt})"):
            st.markdown("**질문 분석:**")
            if thinking_process:
                st.markdown(thinking_process)
            else:
                st.markdown("질문을 분석하여 관련 섹션을 선택했습니다.")
            
            st.markdown("---")
            st.markdown("**선택된 섹션:**")
            for idx, section in enumerate(selected_sections, 1):
                st.markdown(f"{idx}. **{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
        
        # 2단계: 섹션별 벡터 검색 (표와 텍스트 분리 검색) - 병렬 처리
        st.info(f"📄 선택된 {len(selected_sections)}개 섹션에서 표와 텍스트를 분리하여 병렬 검색 중...")
        
        all_retrieved_docs_with_scores = []
        section_results = {}  # 섹션별 검색 결과 저장
        
        # 세션 상태에서 데이터 추출 (병렬 처리 함수에서 접근할 수 있도록)
        section_vectorstores_data = st.session_state.get("section_vectorstores", {})
        
        # 병렬 검색 함수
        def search_section(section, section_vectorstores_data, question, searcher):
            """단일 섹션 검색 함수 (병렬 실행용)
            
            Args:
                section: 섹션 정보 딕셔너리
                section_vectorstores_data: 섹션별 벡터스토어 데이터 (세션 상태에서 추출)
                question: 사용자 질문
                searcher: SearchEngine 인스턴스
            """
            section_key = f"{section['start_page']}_{section['end_page']}"
            section_table_docs = []
            section_text_docs = []
            
            if section_key in section_vectorstores_data:
                section_data = section_vectorstores_data[section_key]
                section_documents = section_data["documents"]
                
                # 표와 텍스트 문서 분리
                table_documents = [doc for doc in section_documents if doc.metadata.get('is_table', False)]
                text_documents = [doc for doc in section_documents if not doc.metadata.get('is_table', False)]
                
                # 표 검색
                if table_documents:
                    try:
                        from langchain_community.vectorstores import FAISS
                        from langchain_google_genai import GoogleGenerativeAIEmbeddings
                        
                        embeddings = GoogleGenerativeAIEmbeddings(model=config.DEFAULT_EMBEDDING_MODEL)
                        table_vectorstore = FAISS.from_documents(documents=table_documents, embedding=embeddings)
                        
                        section_table_docs = searcher.hybrid_search(
                            question=question,
                            vectorstore=table_vectorstore,
                            documents=table_documents,
                            top_k=min(config.TOP_K_PER_SECTION, len(table_documents))
                        )
                    except Exception as e:
                        print(f"⚠️ 섹션 '{section['title']}' 표 검색 중 오류: {str(e)}")
                
                # 텍스트 검색
                if text_documents:
                    try:
                        from langchain_community.vectorstores import FAISS
                        from langchain_google_genai import GoogleGenerativeAIEmbeddings
                        
                        embeddings = GoogleGenerativeAIEmbeddings(model=config.DEFAULT_EMBEDDING_MODEL)
                        text_vectorstore = FAISS.from_documents(documents=text_documents, embedding=embeddings)
                        
                        section_text_docs = searcher.hybrid_search(
                            question=question,
                            vectorstore=text_vectorstore,
                            documents=text_documents,
                            top_k=config.TOP_K_PER_SECTION
                        )
                    except Exception as e:
                        print(f"⚠️ 섹션 '{section['title']}' 텍스트 검색 중 오류: {str(e)}")
            
            return {
                "section": section,
                "section_key": section_key,
                "table_docs": section_table_docs,
                "text_docs": section_text_docs
            }
        
        # ThreadPoolExecutor로 병렬 검색
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_section = {
                executor.submit(search_section, section, section_vectorstores_data, question, searcher): section
                for section in selected_sections
            }
            
            for future in as_completed(future_to_section):
                section = future_to_section[future]
                try:
                    result = future.result()
                    section_table_docs = result["table_docs"]
                    section_text_docs = result["text_docs"]
                    section_docs_with_scores = section_table_docs + section_text_docs
                    all_retrieved_docs_with_scores.extend(section_docs_with_scores)
                    
                    # 섹션별 결과 저장
                    section_results[section['title']] = {
                        "docs": section_docs_with_scores,
                        "table_docs": section_table_docs,
                        "text_docs": section_text_docs,
                        "count": len(section_docs_with_scores),
                        "table_count": len(section_table_docs),
                        "text_count": len(section_text_docs),
                        "section_info": section
                    }
                    
                    st.success(
                        f"✅ 섹션 '{section['title']}' 검색 완료: "
                        f"표 {len(section_table_docs)}개, 텍스트 {len(section_text_docs)}개 "
                        f"(총 {len(section_docs_with_scores)}개)"
                    )
                except Exception as e:
                    st.warning(f"⚠️ 섹션 '{section['title']}' 검색 중 오류: {str(e)}")
                    section_results[section['title']] = {
                        "docs": [],
                        "table_docs": [],
                        "text_docs": [],
                        "count": 0,
                        "table_count": 0,
                        "text_count": 0,
                        "section_info": section,
                        "error": str(e)
                    }
        
        # 섹션별 검색 결과 상세 표시
        with st.expander(f"📊 섹션별 검색 결과 상세 ({len(selected_sections)}개 섹션)"):
            for section_title, result in section_results.items():
                st.markdown(f"### 📑 {section_title}")
                st.markdown(f"**페이지 범위:** {result['section_info']['start_page']}-{result['section_info']['end_page']}페이지")
                st.markdown(f"**검색된 문서 수:** 총 {result['count']}개 (표 {result.get('table_count', 0)}개, 텍스트 {result.get('text_count', 0)}개)")
                
                if result['count'] > 0:
                    # 표 검색 결과
                    if result.get('table_count', 0) > 0:
                        st.markdown("**📊 표 검색 결과:**")
                        for idx, (doc, score) in enumerate(result['table_docs'][:3], 1):  # 상위 3개만 표시
                            with st.container():
                                st.markdown(f"**표 {idx}** (관련성 점수: {score:.3f})")
                                content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                                st.markdown(f"```\n{content_preview}\n```")
                                if idx < len(result['table_docs'][:3]):
                                    st.markdown("---")
                    
                    # 텍스트 검색 결과
                    if result.get('text_count', 0) > 0:
                        st.markdown("**📄 텍스트 검색 결과:**")
                        for idx, (doc, score) in enumerate(result['text_docs'][:5], 1):  # 상위 5개만 표시
                            with st.container():
                                st.markdown(f"**문서 {idx}** (관련성 점수: {score:.3f})")
                                
                                # 메타데이터 정보
                                metadata_info = []
                                chunk_type = doc.metadata.get('chunk_type', 'token')
                                
                                # 페이지 단위 청킹인 경우 페이지 번호 표시
                                if chunk_type == 'page':
                                    page_number = doc.metadata.get('page_number', 0)
                                    page_range = doc.metadata.get('page_range', None)
                                    if page_range:
                                        metadata_info.append(f"📄 페이지 {page_range}")
                                    elif page_number > 0:
                                        metadata_info.append(f"📄 페이지 {page_number}")
                                
                                # 병합된 청크 정보 표시
                                if doc.metadata.get('merged_chunks'):
                                    if chunk_type == 'page':
                                        metadata_info.append(f"🔗 {doc.metadata['merged_chunks']}개 페이지 병합")
                                    else:
                                        metadata_info.append(f"🔗 {doc.metadata['merged_chunks']}개 청크 병합")
                                
                                if metadata_info:
                                    st.markdown(" | ".join(metadata_info))
                                
                                # 문서 내용 미리보기
                                content_preview = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                                st.markdown(f"```\n{content_preview}\n```")
                                
                                if idx < len(result['text_docs'][:5]):
                                    st.markdown("---")
                else:
                    if 'error' in result:
                        st.warning(f"⚠️ {result['error']}")
                    else:
                        st.info("검색된 문서가 없습니다.")
                
                if section_title != list(section_results.keys())[-1]:
                    st.markdown("---")
        
        if not all_retrieved_docs_with_scores:
            st.error("검색된 문서가 없습니다.")
            return {
                "answer": "오류: 관련 문서를 찾을 수 없습니다.",
                "evidence": [],
                "selected_sections": selected_sections
            }
        
        # 3단계: 검색 결과 통합 및 병합
        # 청킹 방식에 따라 메시지 변경
        chunking_type = "페이지 단위" if config.CHUNK_BY_PAGE else "토큰 기반"
        merge_method = "페이지 번호 기반 병합" if config.CHUNK_BY_PAGE else "overlap 정보 기반 병합"
        
        st.info(f"🔗 {len(all_retrieved_docs_with_scores)}개 검색 결과 통합 중... ({merge_method} + 점수 정렬)")
        
        retrieved_docs = rag_system.merge_and_sort_docs(all_retrieved_docs_with_scores)
        st.success(f"✅ 총 {len(retrieved_docs)}개 문서 선택 완료 ({merge_method} + 점수 기반 정렬)")
        
        # 통합된 문서의 섹션별 분포 표시
        with st.expander("📈 최종 통합 문서의 섹션별 분포"):
            section_doc_counts = {}
            for doc in retrieved_docs:
                section_title = doc.metadata.get('section_title', '알 수 없음')
                if section_title not in section_doc_counts:
                    section_doc_counts[section_title] = 0
                section_doc_counts[section_title] += 1
            
            for section_title, count in sorted(section_doc_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(retrieved_docs)) * 100 if retrieved_docs else 0
                st.markdown(f"- **{section_title}**: {count}개 문서 ({percentage:.1f}%)")
        
        # 4단계: 답변 생성 또는 원본 정보 추출
        if extract_only:
            # 테스트 모드: 원본 정보만 추출
            if clean_extract:
                # 순수 정보만 출력 (메타데이터 제외)
                st.info("📋 순수 정보 추출 중... (메타데이터 제외 모드)")
                answer = extract_clean_information(retrieved_docs, question)
            else:
                # 원본 정보 추출 (메타데이터 포함)
                st.info("📋 원본 정보 추출 중... (테스트 모드)")
                answer = extract_raw_information(retrieved_docs, question)
            
            # 품질 평가 건너뛰기
            quality_result = {"is_acceptable": True, "evaluation_text": "테스트 모드: 품질 평가 건너뜀"}
        else:
            # 일반 모드: LLM 답변 생성
            st.info("🤖 답변 생성 중... (직접 컨텍스트 사용 + 대화 맥락 반영)")
            # 이전 대화 히스토리 준비
            conversation_history = []
            if st.session_state["messages"]:
                for msg in st.session_state["messages"]:
                    role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
                    content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                    if role in ["user", "assistant"]:
                        conversation_history.append((role, content))
            
            # 스트리밍 모드로 답변 생성
            answer_chunks = []
            answer_placeholder = st.empty()
            full_answer = ""
            
            # retrieved_docs_with_scores 형태로 변환 (generate_answer가 요구하는 형태)
            retrieved_docs_with_scores = [(doc, doc.metadata.get('similarity_score', 0)) for doc in retrieved_docs]
            
            for chunk in rag_system.generate_answer(question, retrieved_docs_with_scores, conversation_history, stream=True):
                answer_chunks.append(chunk)
                full_answer += chunk
                # 실시간으로 답변 표시
                answer_placeholder.markdown(full_answer)
            
            answer = full_answer
            
            # 5단계: 품질 평가
            st.info("📊 답변 품질 평가 중...")
            quality_result = rag_system.quality_evaluator.evaluate(question, answer)
            
            with st.expander("📋 품질 평가 결과"):
                st.markdown(quality_result["evaluation_text"])
        
        # 근거 문서 정보 수집
        evidence_docs = []
        evidence_by_section = {}  # 섹션별 근거 문서 그룹화
        
        # retrieved_docs는 이미 리스트이므로 그대로 사용
        for doc in retrieved_docs[:10]:
            page_info = ""
            section_info = ""
            
            if hasattr(doc, 'metadata') and doc.metadata:
                is_table = doc.metadata.get('is_table', False)
                table_label = " [표 요약]" if is_table else ""
                chunk_type = doc.metadata.get('chunk_type', 'token')
                
                if 'section_title' in doc.metadata:
                    section_info = doc.metadata['section_title']
                    
                    # 페이지 단위 청킹인 경우 정확한 페이지 번호 표시
                    if chunk_type == 'page':
                        page_number = doc.metadata.get('page_number', 0)
                        page_range = doc.metadata.get('page_range', None)
                        
                        if page_range:
                            # 병합된 페이지 범위
                            page_info = f"섹션: {section_info} (페이지 {page_range}){table_label}"
                        elif page_number > 0:
                            # 단일 페이지
                            page_info = f"섹션: {section_info} (페이지 {page_number}){table_label}"
                        else:
                            # 페이지 번호가 없는 경우 섹션 범위 표시
                            if 'section_start' in doc.metadata and 'section_end' in doc.metadata:
                                page_info = f"섹션: {section_info} (페이지 {doc.metadata['section_start']}-{doc.metadata['section_end']}){table_label}"
                            else:
                                page_info = f"섹션: {section_info}{table_label}"
                    else:
                        # 토큰 기반 청킹: 섹션 범위 표시
                        if 'section_start' in doc.metadata and 'section_end' in doc.metadata:
                            page_info = f"섹션: {section_info} (페이지 {doc.metadata['section_start']}-{doc.metadata['section_end']}){table_label}"
                        else:
                            page_info = f"섹션: {section_info}{table_label}"
            
            # 표의 경우 raw_data 우선 사용
            doc_content = doc.page_content
            if doc.metadata.get('is_table', False) and doc.metadata.get('raw_data'):
                doc_content = doc.metadata['raw_data']
            
            doc_info = {
                "content": doc_content[:500] + "..." if len(doc_content) > 500 else doc_content,
                "page_info": page_info,
                "section_info": section_info,
                "full_content": doc_content,
                "is_table": doc.metadata.get('is_table', False) if hasattr(doc, 'metadata') and doc.metadata else False
            }
            evidence_docs.append(doc_info)
            
            # 섹션별로 그룹화
            if section_info:
                if section_info not in evidence_by_section:
                    evidence_by_section[section_info] = []
                evidence_by_section[section_info].append(doc_info)
        
        # 섹션별 근거 문서 표시
        if evidence_by_section:
            with st.expander("📚 답변에 사용된 섹션별 근거 문서"):
                for section_title, docs in evidence_by_section.items():
                    st.markdown(f"### 📑 {section_title}")
                    st.markdown(f"**사용된 문서 수:** {len(docs)}개")
                    
                    for idx, doc_info in enumerate(docs, 1):
                        st.markdown(f"**근거 {idx}**")
                        if doc_info['is_table']:
                            st.markdown("📊 **표 데이터**")
                        st.markdown(f"*{doc_info['page_info']}*")
                        st.markdown(f"```\n{doc_info['content']}\n```")
                        if idx < len(docs):
                            st.markdown("---")
                    
                    if section_title != list(evidence_by_section.keys())[-1]:
                        st.markdown("---")
        
        # 품질이 적절하면 반환
        if quality_result["is_acceptable"]:
            if attempt > 1:
                st.success(f"✅ {attempt}번째 시도에서 적절한 답변을 생성했습니다!")
            return {
                "answer": answer,
                "evidence": evidence_docs,
                "selected_sections": selected_sections
            }
        else:
            if attempt < max_retries:
                st.warning(f"⚠️ 답변 품질이 부족합니다. 재시도합니다... ({attempt}/{max_retries})")
            else:
                st.warning(f"⚠️ 최대 재시도 횟수({max_retries})에 도달했습니다. 현재 답변을 반환합니다.")
                return {
                    "answer": answer,
                    "evidence": evidence_docs,
                    "selected_sections": selected_sections
                }
    
    return {
        "answer": "오류: 답변 생성에 실패했습니다.",
        "evidence": [],
        "selected_sections": []
    }


# PDF 업로드 처리
if uploaded_file:
    current_pdf = st.session_state.get("pdf_path")
    new_pdf_path = f"{config.FILES_DIR}/{uploaded_file.name}"
    
    # 새 PDF인지 또는 기존 PDF가 변경되었는지 확인
    is_new_pdf = (
        current_pdf is None or 
        current_pdf != new_pdf_path or
        not os.path.exists(current_pdf)
    )
    
    if is_new_pdf:
        # 파일 저장
        file_content = uploaded_file.read()
        pdf_path = new_pdf_path
        with open(pdf_path, "wb") as f:
            f.write(file_content)
        
        st.session_state["pdf_path"] = pdf_path
        
        # 기존 캐시 초기화 (새 PDF 업로드 시)
        if "section_cache" in st.session_state:
            st.session_state["section_cache"] = {}
        if "section_vectorstores" in st.session_state:
            st.session_state["section_vectorstores"] = {}
        if "toc_index" in st.session_state:
            st.session_state["toc_index"] = None
        
        st.session_state["section_cache"] = {}
        st.session_state["section_vectorstores"] = {}
        
        # 목차 인덱스 생성 및 모든 섹션 전처리
        # 파일 수정 시간 가져오기 (캐시 무효화용)
        file_mtime = os.path.getmtime(pdf_path) if os.path.exists(pdf_path) else 0
        result = build_toc_index_and_preprocess(pdf_path, uploaded_file.name, file_mtime)
        
        st.session_state["toc_index"] = result["sections"]
        
        for section_key, data in result["section_data"].items():
            st.session_state["section_vectorstores"][section_key] = data
        
        st.success("✅ PDF 업로드 및 전처리 완료! (목차 분석, 표 인식, 임베딩 생성)")
        st.rerun()

# 초기화 버튼
if clear_btn:
    st.session_state["messages"] = []

# 이전 대화 기록 출력
print_messages()

# 사용자 입력
user_input = st.chat_input("입시 관련 질문을 해주세요!")

warning_msg = st.empty()

# 질의응답 처리
if user_input:
    toc_index = st.session_state.get("toc_index")
    pdf_path = st.session_state.get("pdf_path")
    
    if toc_index and pdf_path:
        st.chat_message("user").write(user_input)
        
        with st.chat_message("assistant"):
            try:
                result = query_with_retry(
                    user_input,
                    pdf_path,
                    toc_index,
                    max_retries,
                    extract_only=extract_only_mode,
                    clean_extract=clean_extract_mode
                )
                
                answer = result["answer"]
                evidence = result.get("evidence", [])
                selected_sections = result.get("selected_sections", [])
                
                if extract_only_mode:
                    if clean_extract_mode:
                        st.markdown("### 📋 추출된 순수 정보 (메타데이터 제외)")
                        st.markdown(answer)
                    else:
                        st.markdown("### 📋 추출된 원본 정보 (테스트 모드)")
                        st.markdown(answer)
                else:
                    st.markdown("### 📝 답변")
                    st.markdown(answer)
                
                # 근거 문서 표시
                if evidence:
                    st.markdown("---")
                    st.markdown("### 📚 답변 근거 (검색된 문서)")
                    st.caption(f"총 {len(evidence)}개의 관련 문서 청크를 참고했습니다.")
                    
                    for idx, doc in enumerate(evidence, 1):
                        expander_title = f"📄 근거 {idx}"
                        if doc['is_table']:
                            expander_title = f"📊 표 요약 {idx}"
                        if doc['page_info']:
                            expander_title += f" - {doc['page_info']}"
                        
                        with st.expander(expander_title):
                            if doc['is_table']:
                                st.markdown("**표 요약 내용:**")
                                st.info("이 내용은 PDF의 표를 AI가 분석하여 요약한 것입니다.")
                            else:
                                st.markdown("**문서 내용:**")
                            st.markdown(doc['content'])
                            if doc['page_info']:
                                st.caption(f"📍 출처: {doc['page_info']}")
                            if len(doc['full_content']) > 500:
                                with st.expander("전체 내용 보기"):
                                    st.markdown(doc['full_content'])
                
                # 선택된 섹션 정보 표시
                if selected_sections:
                    st.markdown("---")
                    st.markdown("### 📋 참고한 섹션")
                    for section in selected_sections:
                        st.markdown(f"- **{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
                
                add_message("user", user_input)
                add_message("assistant", answer)
                
            except Exception as e:
                import traceback
                st.error(f"오류 발생: {str(e)}")
                with st.expander("상세 오류 정보"):
                    st.code(traceback.format_exc())
    else:
        if not pdf_path:
            warning_msg.error("먼저 PDF를 업로드해주세요.")
        elif not toc_index:
            warning_msg.error("PDF 목차 분석이 완료되지 않았습니다. 잠시 후 다시 시도해주세요.")

