"""
개선된 RAG 서비스 (리팩토링 버전)
단계별 필터링으로 효율성 향상
"""
from services.supabase_client import supabase_service
from services.embedding_service import embedding_service
from services.gemini_service import gemini_service
from models.rag_models import SearchResult
from config.constants import IMPORTANT_KEYWORDS, TOP_CHUNKS_COUNT, KEYWORD_DENSITY_WEIGHT
from config.logging_config import rag_logger as logger
import re


class RAGService:
    """개선된 RAG 검색 서비스"""
    
    @staticmethod
    async def search_documents(query: str) -> SearchResult:
        """
        단계별 문서 검색
        
        1단계: 문서 제목/키워드로 관련 문서 필터링 (GPT 판단)
        2단계: 선택된 문서 내에서 핵심 키워드 기반 청크 검색
        3단계: 관련 청크만 반환
        
        Returns:
            {
                'found': bool,
                'chunks': list,
                'source': str,
                'logs': list  # 각 단계 로그
            }
        """
        logs = []
        
        # ============================================================
        # 1단계: 모든 문서의 요약본 가져오기
        # ============================================================
        logs.append(f"📋 1단계: 문서 요약본 조회")
        
        client = supabase_service.get_client()
        response = client.table('policy_documents') \
            .select('id, metadata') \
            .execute()
        
        if not response.data:
            logs.append(f"   ❌ 저장된 문서 없음")
            return SearchResult(
                found=False,
                chunks=[],
                source='',
                logs=logs
            )
        
        # 문서별로 그룹화 (요약본 포함)
        docs_meta = {}
        for row in response.data:
            meta = row.get('metadata', {})
            filename = meta.get('fileName', 'unknown')
            if filename not in docs_meta:
                docs_meta[filename] = {
                    'title': meta.get('title', '제목 없음'),
                    'summary': meta.get('summary', '요약 없음'),  # 요약본 추가
                    'keywords': meta.get('keywords', []),
                    'source': meta.get('source', '출처 없음'),
                    'category': meta.get('categoryName', '미분류')
                }
        
        logs.append(f"   ✅ 총 {len(docs_meta)}개 고유 문서 발견")
        for fname, meta in docs_meta.items():
            logs.append(f"      - {meta['title']}")
            logs.append(f"        요약: {meta['summary'][:80]}...")
        
        # ============================================================
        # 2단계: Gemini로 요약본 기반 문서 필터링
        # ============================================================
        logs.append(f"\n🤖 2단계: Gemini 요약본 기반 문서 필터링")
        
        # 요약본 기반 문서 목록
        docs_summary = "\n\n".join([
            f"{idx+1}. 제목: {meta['title']}\n   요약: {meta['summary']}\n   카테고리: {meta['category']}"
            for idx, (fname, meta) in enumerate(docs_meta.items())
        ])
        
        filter_prompt = f"""다음 문서들의 요약본을 읽고 사용자 질문과 관련있는 문서를 선택하세요.

사용자 질문: "{query}"

문서 목록 (요약본):
{docs_summary}

**선택 방법:**
1. 각 문서의 요약본을 읽고 질문과의 관련성 판단
2. 관련있는 문서 번호를 쉼표로 구분하여 나열
3. 관련 문서가 없으면 "없음"이라고 답변

답변 (번호만):"""
        
        try:
            # Gemini 호출
            filter_result = await gemini_service.generate(
                filter_prompt,
                "당신은 문서 필터링 전문가입니다."
            )
            logs.append(f"   GPT 응답: {filter_result}")
            
            if "없음" in filter_result or not filter_result:
                logs.append(f"   ❌ 관련 문서 없음")
                return SearchResult(
                    found=False,
                    chunks=[],
                    source='',
                    logs=logs
                )
            
            # 번호 추출
            selected_indices = [int(n.strip())-1 for n in re.findall(r'\d+', filter_result)]
            selected_files = [list(docs_meta.keys())[i] for i in selected_indices if i < len(docs_meta)]
            
            logs.append(f"   ✅ {len(selected_files)}개 문서 선택됨")
            for fname in selected_files:
                logs.append(f"      - {docs_meta[fname]['title']}")
            
        except Exception as e:
            logs.append(f"   ⚠️ GPT 필터링 실패, 모든 문서 검색: {e}")
            selected_files = list(docs_meta.keys())
        
        # ============================================================
        # 3단계: 선택된 문서에서 핵심 키워드 추출
        # ============================================================
        logs.append(f"\n🔑 3단계: 질문에서 핵심 키워드 추출")
        
        # 질문에서 명사 추출 (간단한 방법)
        query_keywords = []
        for doc_meta in docs_meta.values():
            for keyword in doc_meta['keywords']:
                if keyword in query:
                    query_keywords.append(keyword)
        
        # 추가로 중요 단어들
        for word in IMPORTANT_KEYWORDS:
            if word in query and word not in query_keywords:
                query_keywords.append(word)
        
        if not query_keywords:
            query_keywords = query.split()[:3]  # 최소한 처음 3단어
        
        logs.append(f"   키워드: {', '.join(query_keywords[:5])}")
        
        # ============================================================
        # 4단계: 선택된 문서의 청크만 가져오기
        # ============================================================
        logs.append(f"\n📄 4단계: 선택된 문서의 청크 조회")
        
        all_chunks = []
        for fname in selected_files:
            response = client.table('policy_documents') \
                .select('content, metadata') \
                .eq('metadata->>fileName', fname) \
                .execute()
            
            if response.data:
                all_chunks.extend(response.data)
                logs.append(f"   {fname}: {len(response.data)}개 청크")
        
        logs.append(f"   ✅ 총 {len(all_chunks)}개 청크")
        
        if not all_chunks:
            logs.append(f"   ❌ 청크 없음")
            return SearchResult(
                found=False,
                chunks=[],
                source='',
                logs=logs
            )
        
        # ============================================================
        # 5단계: 키워드 기반 청크 점수 계산
        # ============================================================
        logs.append(f"\n⭐ 5단계: 키워드 기반 점수 계산")
        
        scored_chunks = []
        for chunk in all_chunks:
            content = chunk['content'].lower()
            score = 0
            
            # 각 키워드가 포함되면 +1점
            for keyword in query_keywords:
                if keyword.lower() in content:
                    score += 1
            
            # 키워드 밀도 보너스 (키워드가 여러 번 나오면 더 높은 점수)
            for keyword in query_keywords[:3]:  # 상위 3개 키워드만
                count = content.count(keyword.lower())
                score += count * KEYWORD_DENSITY_WEIGHT
            
            if score > 0:
                scored_chunks.append({
                    'chunk': chunk,
                    'score': score
                })
        
        # 점수 순으로 정렬
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        logs.append(f"   매칭된 청크: {len(scored_chunks)}개")
        for idx, item in enumerate(scored_chunks[:5], 1):
            logs.append(f"      {idx}. 점수 {item['score']:.1f}: {item['chunk']['content'][:80]}...")
        
        if not scored_chunks:
            logs.append(f"   ❌ 키워드 매칭 실패")
            return SearchResult(
                found=False,
                chunks=[],
                source='',
                logs=logs
            )
        
        # ============================================================
        # 6단계: 상위 청크 반환
        # ============================================================
        logs.append(f"\n✅ 6단계: 상위 {TOP_CHUNKS_COUNT}개 청크 선택")

        top_chunks = [item['chunk'] for item in scored_chunks[:TOP_CHUNKS_COUNT]]
        source = top_chunks[0]['metadata'].get('source', '공식 문서')
        
        logs.append(f"   출처: {source}")
        logs.append(f"   반환 청크: {len(top_chunks)}개")
        
        result = SearchResult(
            found=True,
            chunks=top_chunks,
            source=source,
            logs=logs
        )

        logger.info(f"RAG 검색 완료 - 청크 {len(top_chunks)}개 반환, 출처: {source}")

        return result


# 전역 인스턴스
rag_service = RAGService()

