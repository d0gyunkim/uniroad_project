"""
전역 검색 모드 Streamlit 앱
라우팅 없는 전역 검색 기능을 웹 인터페이스로 제공합니다.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
import numpy as np

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
load_dotenv(override=True)

from core.rag_system import RAGSystem
from supabase import create_client

# 페이지 설정
st.set_page_config(
    page_title="전역 검색 테스트",
    page_icon="🔍",
    layout="wide"
)

# 세션 상태 초기화
if 'rag_system' not in st.session_state:
    st.session_state.rag_system = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'sort_by' not in st.session_state:
    st.session_state.sort_by = 'default'

def get_document_id_from_chunk(supabase_client, chunk_id):
    """chunk_id로 document_id 조회"""
    if not supabase_client or not chunk_id:
        return None
    
    try:
        response = supabase_client.table("document_chunks").select("document_id").eq("id", chunk_id).execute()
        if response.data and response.data[0].get("document_id"):
            return response.data[0].get("document_id")
    except Exception as e:
        print(f"⚠️ chunk_id로 document_id 조회 실패: {e}")
    return None

def get_document_name(supabase_client, document_id):
    """document_id로 문서 이름 조회"""
    if not supabase_client or not document_id:
        return None
    
    try:
        response = supabase_client.table("documents").select("filename").eq("id", document_id).execute()
        if response.data:
            return response.data[0].get("filename")
    except Exception as e:
        print(f"⚠️ 문서 이름 조회 실패: {e}")
    return None

def get_document_names_batch(supabase_client, document_ids):
    """여러 document_id의 문서 이름을 일괄 조회"""
    if not supabase_client or not document_ids:
        return {}
    
    document_names = {}
    unique_ids = list(set([did for did in document_ids if did]))
    
    if not unique_ids:
        return document_names
    
    try:
        response = supabase_client.table("documents").select("id, filename").in_("id", unique_ids).execute()
        for doc in response.data:
            document_names[doc["id"]] = doc.get("filename")
    except Exception as e:
        print(f"⚠️ 문서 이름 일괄 조회 실패: {e}")
    
    return document_names

def get_document_summaries_batch(supabase_client, document_ids):
    """여러 document_id의 summary를 일괄 조회"""
    if not supabase_client or not document_ids:
        return {}
    
    document_summaries = {}
    unique_ids = list(set([did for did in document_ids if did]))
    
    if not unique_ids:
        return document_summaries
    
    try:
        response = supabase_client.table("documents").select("id, summary").in_("id", unique_ids).execute()
        for doc in response.data:
            document_summaries[doc["id"]] = doc.get("summary")
    except Exception as e:
        print(f"⚠️ 문서 summary 일괄 조회 실패: {e}")
    
    return document_summaries

def get_document_summaries_from_chunks(supabase_client, chunk_ids):
    """chunk_id 리스트로 document_id를 조회한 후 summary를 가져오기"""
    if not supabase_client or not chunk_ids:
        return {}
    
    document_summaries = {}
    chunk_to_doc = {}
    
    try:
        # chunk_id로 document_id 조회
        unique_chunk_ids = list(set([cid for cid in chunk_ids if cid]))
        if not unique_chunk_ids:
            return document_summaries
        
        response = supabase_client.table("document_chunks").select("id, document_id").in_("id", unique_chunk_ids).execute()
        
        # chunk_id -> document_id 매핑
        document_ids = []
        for chunk in response.data:
            chunk_id = chunk.get("id")
            doc_id = chunk.get("document_id")
            if chunk_id and doc_id:
                chunk_to_doc[chunk_id] = doc_id
                document_ids.append(doc_id)
        
        # document_id로 summary 조회
        if document_ids:
            unique_doc_ids = list(set(document_ids))
            doc_response = supabase_client.table("documents").select("id, summary").in_("id", unique_doc_ids).execute()
            
            doc_id_to_summary = {}
            for doc in doc_response.data:
                doc_id_to_summary[doc["id"]] = doc.get("summary")
            
            # chunk_id -> summary 매핑
            for chunk_id, doc_id in chunk_to_doc.items():
                document_summaries[chunk_id] = doc_id_to_summary.get(doc_id)
        
    except Exception as e:
        print(f"⚠️ chunk_id로 summary 조회 실패: {e}")
        import traceback
        print(traceback.format_exc())
    
    return document_summaries

def get_document_names_from_chunks(supabase_client, chunk_ids):
    """chunk_id 리스트로 document_id를 조회한 후 문서 이름을 가져오기"""
    if not supabase_client or not chunk_ids:
        return {}
    
    document_names = {}
    chunk_to_doc = {}
    
    try:
        # chunk_id로 document_id 조회
        unique_chunk_ids = list(set([cid for cid in chunk_ids if cid]))
        if not unique_chunk_ids:
            return document_names
        
        response = supabase_client.table("document_chunks").select("id, document_id").in_("id", unique_chunk_ids).execute()
        
        # chunk_id -> document_id 매핑
        document_ids = []
        for chunk in response.data:
            chunk_id = chunk.get("id")
            doc_id = chunk.get("document_id")
            if chunk_id and doc_id:
                chunk_to_doc[chunk_id] = doc_id
                document_ids.append(doc_id)
        
        # document_id로 문서 이름 조회
        if document_ids:
            unique_doc_ids = list(set(document_ids))
            doc_response = supabase_client.table("documents").select("id, filename").in_("id", unique_doc_ids).execute()
            
            doc_id_to_name = {}
            for doc in doc_response.data:
                doc_id_to_name[doc["id"]] = doc.get("filename")
            
            # chunk_id -> document_name 매핑
            for chunk_id, doc_id in chunk_to_doc.items():
                document_names[chunk_id] = doc_id_to_name.get(doc_id)
        
    except Exception as e:
        print(f"⚠️ chunk_id로 문서 이름 조회 실패: {e}")
        import traceback
        print(traceback.format_exc())
    
    return document_names

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

def calculate_metadata_similarities(results, document_summaries, query, embeddings, content_weight=0.6, summary_weight=0.4):
    """각 청크의 내용 유사도와 summary 유사도, 그리고 가중평균 계산"""
    if not embeddings or not query:
        return {}
    
    try:
        # 쿼리 임베딩
        query_embedding = embeddings.embed_query(query)
        
        similarities = {}
        
        for i, result in enumerate(results):
            content_similarity = 0.0
            summary_similarity = 0.0
            weighted_average = 0.0
            
            # 청크 내용 유사도 계산
            content = result.get('content', '')
            if content:
                try:
                    # 성능 최적화: 처음 2000자만 사용
                    content_text = content[:2000] if len(content) > 2000 else content
                    content_embedding = embeddings.embed_query(content_text)
                    content_similarity = calculate_cosine_similarity(query_embedding, content_embedding)
                except Exception as e:
                    print(f"⚠️ 내용 유사도 계산 실패: {e}")
                    content_similarity = 0.0
            
            # summary 유사도 계산
            summary = result.get('summary', '')
            if not summary and isinstance(document_summaries, dict) and i in document_summaries:
                summary = document_summaries.get(i, '')
            
            if summary:
                try:
                    summary_embedding = embeddings.embed_query(summary)
                    summary_similarity = calculate_cosine_similarity(query_embedding, summary_embedding)
                except Exception as e:
                    print(f"⚠️ Summary 유사도 계산 실패: {e}")
                    summary_similarity = 0.0
            
            # 가중평균 계산 (내용 유사도와 Summary 유사도)
            if content_similarity > 0 or summary_similarity > 0:
                weighted_average = (content_similarity * content_weight) + (summary_similarity * summary_weight)
            
            similarities[i] = {
                'content_similarity': content_similarity,
                'summary_similarity': summary_similarity,
                'weighted_average': weighted_average
            }
        
        return similarities
    except Exception as e:
        print(f"⚠️ 유사도 계산 실패: {e}")
        return {}

def initialize_rag_system():
    """RAG 시스템 초기화"""
    if st.session_state.initialized and st.session_state.rag_system:
        return st.session_state.rag_system
    
    # 환경 변수 확인
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("❌ Supabase 환경 변수가 설정되지 않았습니다.\n\n.env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요.")
        return None
    
    if not gemini_key:
        st.error("❌ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.\n\n.env 파일에 GEMINI_API_KEY를 설정하세요.")
        return None
    
    # RAG 시스템 초기화
    with st.spinner("📦 RAG 시스템 초기화 중..."):
        try:
            rag_system = RAGSystem()
            st.session_state.rag_system = rag_system
            st.session_state.initialized = True
            return rag_system
        except Exception as e:
            st.error(f"❌ RAG 시스템 초기화 실패: {str(e)}")
            st.exception(e)
            return None

def main():
    """메인 함수"""
    st.title("🔍 전역 검색 모드 테스트")
    st.markdown("라우팅 없는 전역 검색 기능을 테스트합니다.")
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 초기화 버튼
        if st.button("🔄 시스템 초기화", use_container_width=True):
            st.session_state.rag_system = None
            st.session_state.initialized = False
            st.rerun()
        
        st.divider()
        
        # 검색 설정
        st.subheader("검색 설정")
        top_k = st.slider("초기 검색 개수 (top_k)", min_value=10, max_value=100, value=30, step=10)
        display_count = st.slider("표시할 청크 개수", min_value=1, max_value=20, value=10, step=1)
        
        st.divider()
        
        # 정보
        st.info("💡 **사용 방법**\n\n1. 학교 이름을 입력하세요\n2. 검색 질문을 입력하세요\n3. 검색 버튼을 클릭하세요")
    
    # RAG 시스템 초기화
    rag_system = initialize_rag_system()
    
    if not rag_system:
        st.stop()
    
    # 메인 영역
    col1, col2 = st.columns([1, 1])
    
    with col1:
        school_name = st.text_input(
            "🏫 학교 이름",
            value="고려대학교",
            placeholder="예: 고려대학교, 서울대학교, 경희대학교"
        )
    
    with col2:
        query = st.text_input(
            "❓ 검색 질문",
            value="수시 전형 모집인원",
            placeholder="검색할 질문을 입력하세요"
        )
    
    # 검색 버튼
    if st.button("🔍 검색 실행", type="primary", use_container_width=True):
        if not school_name or not query:
            st.warning("⚠️ 학교 이름과 검색 질문을 모두 입력해주세요.")
            st.stop()
        
        # 검색 진행 표시
        with st.spinner(f"🔍 '{query}' 검색 중... (학교: {school_name})"):
            try:
                # 전역 검색 수행 (가중 평균 유사도 상위 10개 반환)
                results = rag_system.search_global_raw(
                    school_name=school_name,
                    query=query,
                    top_k=top_k
                )
                
                if not results:
                    st.warning("⚠️ 검색 결과가 없습니다.")
                    st.stop()
                
                # 결과 요약
                st.success(f"✅ 검색 완료: {len(results)}개 청크 발견 (가중 평균 유사도 상위 10개)")
                
                # 상위 N개 청크 표시
                display_results = results[:display_count]
                
                # Supabase 클라이언트 초기화
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_KEY")
                
                if not supabase_url or not supabase_key:
                    st.error("❌ Supabase 환경 변수가 설정되지 않았습니다.")
                    st.stop()
                
                supabase_client = create_client(supabase_url, supabase_key)
                
                # chunk_id로 실제 청크 정보 조회
                chunk_ids = [r.get('chunk_id') for r in display_results if r.get('chunk_id')]
                
                # 청크 정보 조회
                chunks_info = {}
                if chunk_ids:
                    try:
                        response = supabase_client.table("document_chunks").select(
                            "id, content, raw_data, page_number, chunk_type, section_id, document_id"
                        ).in_("id", chunk_ids).execute()
                        
                        for chunk in response.data:
                            chunk_id = chunk.get("id")
                            chunks_info[chunk_id] = {
                                "content": chunk.get("raw_data") or chunk.get("content", ""),
                                "page_number": chunk.get("page_number", 0),
                                "chunk_type": chunk.get("chunk_type", "text"),
                                "section_id": chunk.get("section_id"),
                                "document_id": chunk.get("document_id")
                            }
                    except Exception as e:
                        st.error(f"❌ 청크 정보 조회 실패: {e}")
                        st.stop()
                
                # 문서 이름 및 summary 조회
                document_names = {}
                document_summaries = {}
                document_ids = [r.get('document_id') for r in display_results if r.get('document_id')]
                
                # document_id로 문서 이름 및 summary 조회
                if document_ids:
                    try:
                        unique_doc_ids = list(set(document_ids))
                        doc_names_by_id = get_document_names_batch(supabase_client, unique_doc_ids)
                        doc_summaries_by_id = get_document_summaries_batch(supabase_client, unique_doc_ids)
                        
                        # 결과에 문서 이름과 summary 매핑
                        for result in display_results:
                            doc_id = result.get('document_id')
                            chunk_id = result.get('chunk_id')
                            if doc_id and doc_id in doc_names_by_id:
                                result['document_name'] = doc_names_by_id[doc_id]
                            if doc_id and doc_id in doc_summaries_by_id:
                                result['summary'] = doc_summaries_by_id[doc_id]
                            # 청크 정보도 추가
                            if chunk_id and chunk_id in chunks_info:
                                result.update(chunks_info[chunk_id])
                    except Exception as e:
                        st.warning(f"⚠️ 문서 정보 조회 중 오류: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                
                # 메타데이터 유사도 계산 (summary와 내용 유사도, 가중평균)
                metadata_similarities = {}
                if rag_system.embeddings:
                    with st.spinner("📊 유사도 계산 중..."):
                        # display_results에서 summary 추출
                        summaries_dict = {}
                        for i, result in enumerate(display_results):
                            if 'summary' in result:
                                summaries_dict[i] = result.get('summary', '')
                        
                        metadata_similarities = calculate_metadata_similarities(
                            display_results, summaries_dict, query, rag_system.embeddings
                        )
                
                # 정렬 기준 선택
                st.divider()
                st.subheader("🔄 정렬 기준 선택")
                
                sort_options = {
                    "기본 (내용 유사도)": "default",
                    "내용 유사도": "content",
                    "Summary 유사도": "summary",
                    "가중평균": "weighted"
                }
                
                col_sort1, col_sort2, col_sort3, col_sort4 = st.columns(4)
                
                with col_sort1:
                    if st.button("📄 기본", use_container_width=True, key="sort_default"):
                        st.session_state.sort_by = "default"
                        st.rerun()
                
                with col_sort2:
                    if st.button("📝 내용", use_container_width=True, key="sort_content"):
                        st.session_state.sort_by = "content"
                        st.rerun()
                
                with col_sort3:
                    if st.button("📄 Summary", use_container_width=True, key="sort_summary"):
                        st.session_state.sort_by = "summary"
                        st.rerun()
                
                with col_sort4:
                    if st.button("⚖️ 가중평균", use_container_width=True, key="sort_weighted"):
                        st.session_state.sort_by = "weighted"
                        st.rerun()
                
                # 선택된 정렬 기준에 따라 재정렬
                sort_by = st.session_state.get('sort_by', 'default')
                
                if sort_by != 'default' and metadata_similarities:
                    # 유사도 기준으로 정렬 (결과와 유사도 정보를 함께 정렬)
                    results_with_sim = list(zip(display_results, [metadata_similarities.get(i, {}) for i in range(len(display_results))]))
                    
                    sort_key_map = {
                        'content': 'content_similarity',
                        'summary': 'summary_similarity',
                        'weighted': 'weighted_average'
                    }
                    
                    sort_key = sort_key_map.get(sort_by, 'content_similarity')
                    
                    results_with_sim.sort(
                        key=lambda x: x[1].get(sort_key, 0.0),
                        reverse=True
                    )
                    
                    # 정렬된 결과 분리
                    display_results = [r[0] for r in results_with_sim]
                    metadata_similarities = {i: r[1] for i, r in enumerate(results_with_sim)}
                
                # 정렬 기준 표시
                if sort_by != 'default':
                    sort_label = {
                        'content': '내용 유사도',
                        'summary': 'Summary 유사도',
                        'weighted': '가중평균'
                    }.get(sort_by, '기본')
                    st.info(f"📌 현재 정렬 기준: **{sort_label}**")
                
                # 결과를 탭으로 구분
                tab1, tab2 = st.tabs(["📋 상세 보기", "📊 요약 보기"])
                
                with tab1:
                    # 각 청크 상세 정보
                    for i, result in enumerate(display_results, 1):
                        # 유사도 정보 가져오기
                        sim_info = metadata_similarities.get(i-1, {})
                        content_sim = sim_info.get('content_similarity', 0.0)
                        summary_sim = sim_info.get('summary_similarity', 0.0)
                        weighted_avg = sim_info.get('weighted_average', 0.0)
                        
                        # 제목에 유사도 정보 추가
                        title_suffix = ""
                        if sort_by == 'content':
                            title_suffix = f" (내용 유사도: {content_sim:.4f})"
                        elif sort_by == 'summary':
                            title_suffix = f" (Summary 유사도: {summary_sim:.4f})"
                        elif sort_by == 'weighted':
                            title_suffix = f" (가중평균: {weighted_avg:.4f})"
                        
                        with st.expander(f"📄 청크 #{i} (가중평균: {weighted_avg:.4f}){title_suffix}", expanded=(i == 1)):
                            # 메타데이터
                            col_meta1, col_meta2, col_meta3 = st.columns(3)
                            
                            with col_meta1:
                                st.metric("페이지", result.get('page_number', 'N/A'))
                            
                            with col_meta2:
                                st.metric("청크 ID", result.get('chunk_id', 'N/A'))
                            
                            with col_meta3:
                                st.metric("청크 타입", result.get('chunk_type', 'N/A'))
                            
                            # 메타데이터 유사도 표시
                            if metadata_similarities:
                                st.divider()
                                st.markdown("**📊 유사도 정보:**")
                                col_sim1, col_sim2, col_sim3 = st.columns(3)
                                
                                with col_sim1:
                                    st.metric("내용 유사도", f"{content_sim:.4f}")
                                
                                with col_sim2:
                                    st.metric("Summary 유사도", f"{summary_sim:.4f}")
                                
                                with col_sim3:
                                    st.metric("가중평균", f"{weighted_avg:.4f}")
                            
                            st.divider()
                            
                            # 추가 정보
                            info_cols = st.columns(3)
                            with info_cols[0]:
                                document_name = result.get('document_name', '정보 없음')
                                st.markdown(f"**📄 문서:** {document_name}")
                                document_id = result.get('document_id')
                                if document_id:
                                    st.caption(f"*문서 ID: {document_id}*")
                            
                            with info_cols[1]:
                                section_id = result.get('section_id')
                                if section_id:
                                    st.caption(f"**섹션 ID:** {section_id}")
                                else:
                                    st.caption("**섹션 ID:** 정보 없음")
                            
                            with info_cols[2]:
                                chunk_id = result.get('chunk_id', 'N/A')
                                st.caption(f"**청크 ID:** {chunk_id}")
                            
                            st.divider()
                            
                            # 청크 내용
                            content = result.get('content', '')
                            if content:
                                st.markdown("**내용:**")
                                st.text_area(
                                    "청크 내용",
                                    value=content,
                                    height=200,
                                    disabled=True,
                                    key=f"content_{i}",
                                    label_visibility="collapsed"
                                )
                                
                                # 내용 길이 정보
                                if len(content) > 500:
                                    st.caption(f"📏 내용 길이: {len(content):,}자")
                            else:
                                st.info("⚠️ 청크 내용을 불러올 수 없습니다.")
                
                with tab2:
                    # 요약 테이블
                    import pandas as pd
                    
                    summary_data = []
                    for i, result in enumerate(display_results, 1):
                        document_name = result.get('document_name', '-')
                        sim_info = metadata_similarities.get(i-1, {})
                        content = result.get('content', '')
                        
                        summary_data.append({
                            "순위": i,
                            "청크 ID": result.get('chunk_id', 'N/A'),
                            "섹션 ID": result.get('section_id', 'N/A'),
                            "문서 ID": result.get('document_id', 'N/A'),
                            "문서": document_name,
                            "페이지": result.get('page_number', 'N/A'),
                            "내용 유사도": f"{sim_info.get('content_similarity', 0.0):.4f}",
                            "Summary 유사도": f"{sim_info.get('summary_similarity', 0.0):.4f}",
                            "가중평균": f"{sim_info.get('weighted_average', 0.0):.4f}",
                            "청크 타입": result.get('chunk_type', 'N/A'),
                            "내용 길이": len(content)
                        })
                    
                    df = pd.DataFrame(summary_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # 통계 정보
                    st.divider()
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    
                    with col_stat1:
                        st.metric("총 검색 결과", len(results))
                    
                    with col_stat2:
                        st.metric("표시된 청크", len(display_results))
                    
                    with col_stat3:
                        avg_score = sum(r.get('score', 0.0) for r in display_results) / len(display_results) if display_results else 0
                        st.metric("평균 유사도", f"{avg_score:.4f}")
                
            except Exception as e:
                st.error(f"❌ 오류 발생: {str(e)}")
                st.exception(e)

if __name__ == "__main__":
    main()

