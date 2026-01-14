"""
에이전트 기반 RAG 서비스
LLM이 필요할 때만 문서를 검색하는 자연스러운 대화 시스템
"""
from services.supabase_client import supabase_service
from services.gemini_service import gemini_service
from google.generativeai.types import FunctionDeclaration
from typing import List, Dict, Any
import json


class AgentService:
    """에이전트 기반 대화 서비스"""

    # search_documents 도구 선언
    SEARCH_TOOL = FunctionDeclaration(
        name="search_documents",
        description=(
            "대학 입시 관련 공식 문서를 검색합니다. "
            "구체적인 수치, 날짜, 규정, 전형 방법 등 정확한 정보가 필요할 때 사용하세요. "
            "일반적인 위로나 격려는 검색 없이 답변하세요."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색할 키워드 (예: '2028학년도 서울대 정시 교과평가', '학생부종합전형 평가요소')"
                }
            },
            "required": ["query"]
        }
    )

    SYSTEM_INSTRUCTION = """당신은 친근하고 따뜻한 대학 입시 전문 상담사입니다.

🚫 절대 금지 사항:
1. 마크다운 문법 사용 금지: #, ##, ###, *, **, ___, -, 등 절대 사용하지 마세요
2. 한 번에 많은 정보를 쏟아내지 마세요
3. 막연한 질문에 바로 검색하지 마세요 (먼저 구체화 필요)

⚠️ 검색 타이밍 판단 (매우 중요!):
막연한 질문 예시:
- "서울대 가고싶어", "연세대 궁금해" → 검색 X, 먼저 "수시/정시 중 어느 전형이 궁금하세요?" 물어보기
- "불안해", "힘들어" → 검색 X, 공감하고 구체적으로 무엇이 걱정인지 물어보기
- "입시 준비 어떻게 해?" → 검색 X, 현재 학년과 목표를 먼저 물어보기

구체적인 질문 예시:
- "서울대 2028 정시 변경사항 알려줘" → 검색 O
- "학생부종합전형 평가 요소가 뭐야?" → 검색 O
- "지역균형전형 추천 인원 몇 명이야?" → 검색 O

✅ 대화 방식:
1단계: 막연한 질문이면
   - 공감과 격려 (1-2문장)
   - 구체적으로 어떤 정보가 필요한지 물어보기
   - 검색 절대 하지 않기!

2단계: 구체적인 질문이면
   - search_documents로 정보 검색
   - 찾은 정보만 <cite>로 감싸기
   - 추가 궁금한 점 물어보기

✅ 답변 형식:
- 일반 텍스트로만 작성 (마크다운 절대 금지)
- 짧고 간결하게 (3-4문장 이내)
- 번호는 "1. 2. 3." 형식만 허용

✅ 출처 표시 (<cite> 태그) - 매우 중요!:
- 검색으로 찾은 내용만 <cite>로 감싸기
- <cite> 태그 개수 = 실제 출처 개수와 정확히 일치해야 함
- 출처가 하나면 <cite> 하나, 출처가 두 개면 <cite> 두 개
- 일반 조언/격려/추측은 절대 <cite> 사용 금지

올바른 예시:
학생: "서울대 가고싶어"
답변: "서울대를 목표로 하시는군요! 정말 멋진 목표예요. 혹시 수시와 정시 중 어느 전형이 더 궁금하신가요? 아니면 특정 학과가 있으신가요?"
→ 검색 없음, 구체화 질문만

학생: "서울대 2028 정시 변경사항 알려줘"
답변: "네, 중요한 변화가 있어요. <cite>2028학년도부터 서울대 정시에서는 학생부 교과평가가 40% 반영됩니다</cite>. 다른 변경사항도 궁금하신가요?"
→ 검색 후 cite 1개만 사용

잘못된 예시:
"서울대 가고싶어" → "<cite>정시에서 교과평가 40%</cite>" (X)
막연한 질문에 바로 검색하지 마세요!
"""

    @staticmethod
    async def search_documents(query: str) -> Dict[str, Any]:
        """
        문서 검색 도구 실행

        Returns:
            {
                "found": bool,
                "content": str,
                "sources": List[str],
                "source_urls": List[str]
            }
        """
        print(f"\n{'='*80}")
        print(f"🔍 search_documents 호출: {query}")
        print(f"{'='*80}")

        try:
            client = supabase_service.get_client()

            # 1. documents_metadata에서 관련 문서 찾기
            metadata_response = client.table('documents_metadata').select('*').execute()

            if not metadata_response.data:
                return {"found": False, "content": "", "sources": [], "source_urls": []}

            # 1단계: 해시태그 추출 (질문에서 키워드 분석)
            print(f"   📋 [1단계] 질문 분석 중...")
            print(f"   원본 질문: \"{query}\"")
            
            query_lower = query.lower()
            extracted_hashtags = []
            
            # 연도 추출
            import re
            year_match = re.search(r'(2025|2026|2027)', query)
            if year_match:
                extracted_hashtags.append(f'#{year_match.group()}')
                print(f"   ✓ 연도 감지: #{year_match.group()}")
            
            # 대학명 추출
            universities = ['서울대', '연세대', '고려대', '성균관대', '한양대', '중앙대', '경희대', '이화여대']
            for univ in universities:
                if univ in query:
                    extracted_hashtags.append(f'#{univ}')
                    print(f"   ✓ 대학명 감지: #{univ}")
            
            # 문서 성격 추출
            if any(word in query for word in ['요강', '모집', '전형']):
                extracted_hashtags.append('#모집요강')
                print(f"   ✓ 문서 성격: #모집요강")
            elif any(word in query for word in ['입결', '경쟁률', '커트', '합격선']):
                extracted_hashtags.append('#입결통계')
                print(f"   ✓ 문서 성격: #입결통계")
            elif any(word in query for word in ['논술', '면접', '기출']):
                extracted_hashtags.append('#고사자료')
                print(f"   ✓ 문서 성격: #고사자료")
            
            # 전형 구분
            if '수시' in query:
                extracted_hashtags.append('#수시')
                print(f"   ✓ 전형: #수시")
            if '정시' in query:
                extracted_hashtags.append('#정시')
                print(f"   ✓ 전형: #정시")
            
            print(f"   🏷️ 최종 추출 해시태그: {extracted_hashtags}")

            # 2단계: 해시태그 매칭 + 키워드 매칭으로 문서 찾기
            print(f"\n   📋 [2단계] 문서 검색 중...")
            print(f"   전체 문서 수: {len(metadata_response.data)}개")
            
            relevant_docs = []
            query_keywords = query_lower.split()

            for doc in metadata_response.data:
                title = doc.get('title', '').lower()
                summary = doc.get('summary', '').lower()
                doc_hashtags = doc.get('hashtags', [])
                
                score = 0
                matched_info = []
                
                # 해시태그 매칭 (우선순위 높음)
                if doc_hashtags and extracted_hashtags:
                    matching_tags = set(doc_hashtags) & set(extracted_hashtags)
                    if matching_tags:
                        score += len(matching_tags) * 10  # 해시태그 매칭은 10점
                        matched_info.append(f"태그 {len(matching_tags)}개 일치: {matching_tags}")
                
                # 키워드 매칭 (기존 방식, 우선순위 낮음)
                keyword_matches = sum(1 for kw in query_keywords if kw in title or kw in summary)
                if keyword_matches > 0:
                    score += keyword_matches
                    matched_info.append(f"키워드 {keyword_matches}개 일치")
                
                if score > 0:
                    print(f"   • {doc.get('title')} (점수: {score}) - {', '.join(matched_info)}")
                    print(f"     해시태그: {doc_hashtags}")
                    relevant_docs.append((score, doc))
            
            # 점수 순으로 정렬
            relevant_docs.sort(key=lambda x: x[0], reverse=True)
            relevant_docs = [doc for score, doc in relevant_docs]

            if not relevant_docs:
                print("   ❌ 관련 문서 없음")
                print(f"{'='*80}\n")
                return {"found": False, "content": "", "sources": [], "source_urls": []}

            print(f"\n   ✅ 최종 선택: 상위 {min(3, len(relevant_docs))}개 문서")

            # 2. 관련 문서의 전체 청크 가져오기
            print(f"\n   📋 [3단계] 문서 내용 로드 중...")
            
            full_content = ""
            sources = []
            source_urls = []

            for idx, doc in enumerate(relevant_docs[:3], 1):  # 최대 3개 문서
                filename = doc['file_name']
                title = doc['title']
                file_url = doc.get('file_url') or ''  # None이면 빈 문자열
                
                sources.append(title)
                source_urls.append(file_url)

                print(f"   [{idx}] 📄 {title}")
                print(f"       출처: {doc.get('source')}")
                print(f"       해시태그: {doc.get('hashtags', [])}")

                # 해당 문서의 모든 청크 가져오기
                chunks_response = client.table('policy_documents')\
                    .select('content, metadata')\
                    .eq('metadata->>fileName', filename)\
                    .execute()

                if chunks_response.data:
                    # 청크 순서대로 정렬
                    sorted_chunks = sorted(
                        chunks_response.data,
                        key=lambda x: x.get('metadata', {}).get('chunkIndex', 0)
                    )
                    
                    print(f"       청크 수: {len(sorted_chunks)}개")

                    full_content += f"\n\n{'='*60}\n"
                    full_content += f"📄 {title}\n"
                    full_content += f"{'='*60}\n\n"

                    for chunk in sorted_chunks:
                        full_content += chunk['content']
                        full_content += "\n\n"

            print(f"\n   📊 전체 문서 내용:")
            print(f"       총 길이: {len(full_content):,}자")
            print(f"       앞부분 미리보기 (300자):")
            print(f"       {'-'*60}")
            print(f"       {full_content[:300]}...")
            print(f"       {'-'*60}")
            print(f"{'='*80}\n")

            return {
                "found": True,
                "content": full_content,
                "sources": sources,
                "source_urls": source_urls
            }

        except Exception as e:
            print(f"   ❌ 검색 오류: {e}")
            print(f"{'='*80}\n")
            return {"found": False, "content": "", "sources": [], "source_urls": []}

    @staticmethod
    async def chat(user_message: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        에이전트 기반 대화 처리

        Args:
            user_message: 사용자 메시지
            history: 대화 히스토리 (선택)

        Returns:
            {
                "response": str,
                "sources": List[str],
                "used_search": bool
            }
        """
        print(f"\n{'#'*80}")
        print(f"# 🤖 에이전트 대화 시작")
        print(f"# 사용자 질문: {user_message}")
        print(f"# 대화 히스토리: {len(history) if history else 0}턴")
        print(f"{'#'*80}\n")

        # 대화 히스토리 구성 (복사본 사용 - 원본 오염 방지)
        if history is None:
            history = []

        # 현재 요청용 messages (function call 내역 포함)
        messages = history.copy() + [{"role": "user", "parts": [user_message]}]

        # Tool 사용 대화 (최대 5번 루프)
        sources = []
        source_urls = []
        used_search = False

        for turn in range(5):
            print(f"{'~'*80}")
            print(f"턴 {turn + 1}")
            print(f"{'~'*80}")

            # Gemini 호출 (tools 포함)
            response = await gemini_service.chat_with_tools(
                messages=messages,
                tools=[AgentService.SEARCH_TOOL],
                system_instruction=AgentService.SYSTEM_INSTRUCTION
            )

            if response["type"] == "text":
                # 최종 답변
                print(f"\n{'='*80}")
                print(f"✅ 최종 답변 생성 완료!")
                print(f"{'='*80}")
                print(f"답변 길이: {len(response['content'])}자")
                print(f"출처 수: {len(sources)}개")
                print(f"문서 검색 사용: {'Yes' if used_search else 'No'}")
                print(f"\n📝 최종 답변:")
                print(f"{'-'*80}")
                print(f"{response['content']}")
                print(f"{'-'*80}")
                print(f"{'#'*80}\n")

                return {
                    "response": response["content"],
                    "sources": sources,
                    "source_urls": source_urls,
                    "used_search": used_search
                }

            elif response["type"] == "function_call":
                # Function Call 발생
                fc = response["function_call"]
                func_name = fc["name"]
                func_args = fc["args"]
                raw_response = response["raw_response"]

                print(f"\n🔧 Gemini Function Call 결정:")
                print(f"   함수명: {func_name}")
                print(f"   인자: {func_args}")

                if func_name == "search_documents":
                    # 문서 검색 실행
                    search_result = await AgentService.search_documents(func_args["query"])
                    used_search = True

                    if search_result["found"]:
                        sources.extend(search_result["sources"])
                        source_urls.extend(search_result.get("source_urls", []))

                        # 🚀 Gemini 2.5 Flash Lite로 문서에서 정보 추출 (빠른 처리)
                        print(f"\n   📋 [4단계] Gemini Lite로 정보 추출 중...")
                        print(f"   입력 문서 길이: {len(search_result['content']):,}자")
                        print(f"   입력 문서 미리보기 (300자):")
                        print(f"   {'-'*60}")
                        print(f"   {search_result['content'][:300]}...")
                        print(f"   {'-'*60}")
                        
                        extracted_info = await gemini_service.extract_info_from_documents(
                            query=func_args["query"],
                            documents=search_result['content'],
                            system_instruction="당신은 문서에서 핵심 정보를 정확하게 추출하는 전문가입니다."
                        )
                        
                        print(f"\n   ✅ 정보 추출 완료:")
                        print(f"   출력 길이: {len(extracted_info)}자")
                        print(f"   추출 내용:")
                        print(f"   {'-'*60}")
                        print(f"   {extracted_info}")
                        print(f"   {'-'*60}")

                        # 추출된 정보만 전달 (전체 문서 대신)
                        result_text = f"검색 결과:\n\n{extracted_info}"
                        result_text_summary = f"[문서 {len(search_result['sources'])}개 검색 완료: {', '.join(search_result['sources'])}]"
                        
                        print(f"\n   📋 [5단계] Gemini에게 전달할 최종 결과:")
                        print(f"   {result_text_summary}")
                        print(f"   전달 내용 길이: {len(result_text)}자")
                    else:
                        result_text = "관련 문서를 찾지 못했습니다. 일반적인 지식으로 답변해주세요."
                        result_text_summary = result_text
                        print(f"\n   ⚠️ 문서를 찾지 못함 → 일반 지식으로 답변")

                    # Gemini SDK를 사용해서 function response 생성
                    from google.ai.generativelanguage_v1beta.types import content as glm_content

                    # Function 결과를 대화에 추가 (원본 응답의 content 사용)
                    messages.append({
                        "role": "model",
                        "parts": [raw_response.candidates[0].content.parts[0]]
                    })

                    # Function response 추가 (전체 내용 전달)
                    function_response = glm_content.Part(
                        function_response=glm_content.FunctionResponse(
                            name=func_name,
                            response={"result": result_text}
                        )
                    )

                    messages.append({
                        "role": "user",
                        "parts": [function_response]
                    })

                    print(f"\n   ✅ Function Response를 대화에 추가:")
                    print(f"   전체 대화 길이: {len(messages)}개 메시지")

        # 최대 턴 초과
        print(f"⚠️ 최대 턴 수 초과")
        print(f"{'#'*80}\n")

        return {
            "response": "죄송합니다. 답변 생성 중 문제가 발생했습니다. 다시 질문해주세요.",
            "sources": sources,
            "source_urls": source_urls,
            "used_search": used_search
        }


# 전역 인스턴스
agent_service = AgentService()
