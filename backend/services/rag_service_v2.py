"""
새로운 RAG 서비스 (Query Rewrite + 요약본 기반 문서 선택 + 전체 문서 전달)
"""
from services.supabase_client import supabase_service
from services.gemini_service import gemini_service
import re


class RAGServiceV2:
    """개선된 RAG 서비스 - Gemini가 모든 걸 처리"""

    @staticmethod
    async def rewrite_query(user_query: str) -> str:
        """
        1단계: Query Rewrite
        학생들의 캐주얼한 질문을 검색 가능한 형태로 변환
        """
        print(f"\n{'='*80}")
        print(f"📝 1단계: Query Rewrite (질문 다듬기)")
        print(f"{'='*80}")
        print(f"원본 질문: {user_query}")

        prompt = f"""다음은 고등학생이 대학 입시에 대해 질문한 내용입니다.
이 질문을 검색하기 좋은 형태로 바꿔주세요.

원본 질문: "{user_query}"

변환 규칙:
1. 줄임말을 풀어쓰기 (예: "학종" → "학생부종합전형", "내신" → "학교생활기록부 성적")
2. 구어체를 문어체로 (예: "뭐임?" → "무엇인가요?", "알려줘" → "알려주세요")
3. 핵심 키워드 명확히 포함 (연도, 전형명, 대학명 등)
4. 한 문장으로 명확하게 작성
5. 존댓말로 변환

변환된 질문만 답변하세요 (설명 없이):"""

        try:
            rewritten = await gemini_service.generate(
                prompt,
                system_instruction="당신은 질문을 검색 가능한 형태로 변환하는 전문가입니다."
            )

            rewritten = rewritten.strip()
            print(f"✅ 변환된 질문: {rewritten}")
            print(f"{'='*80}\n")

            return rewritten

        except Exception as e:
            print(f"⚠️ Query Rewrite 실패, 원본 사용: {e}")
            print(f"{'='*80}\n")
            return user_query

    @staticmethod
    async def select_documents(rewritten_query: str) -> list[str]:
        """
        2단계: 문서 선택
        모든 문서의 요약본을 Gemini에게 보여주고 관련 문서 선택
        """
        print(f"{'='*80}")
        print(f"📚 2단계: 문서 선택 (요약본 기반)")
        print(f"{'='*80}")

        # documents_metadata 테이블에서 모든 문서의 요약본 가져오기
        client = supabase_service.get_client()
        response = client.table('documents_metadata').select('*').execute()

        if not response.data:
            print("❌ 저장된 문서가 없습니다")
            print(f"{'='*80}\n")
            return []

        # 문서 목록 구성
        docs_summary = {}
        for row in response.data:
            filename = row.get('file_name', 'unknown')
            docs_summary[filename] = {
                'title': row.get('title', '제목 없음'),
                'summary': row.get('summary', '요약 없음'),
                'category': '미분류',  # 나중에 추가 예정
                'source': row.get('source', '출처 없음')
            }

        print(f"📋 총 {len(docs_summary)}개 문서 발견")
        for idx, (filename, info) in enumerate(docs_summary.items(), 1):
            print(f"   {idx}. [{info['category']}] {info['title']}")
            print(f"      파일: {filename}")
            print(f"      요약: {info['summary'][:100]}...")

        # 요약본 목록을 텍스트로 만들기
        summary_text = ""
        for idx, (filename, info) in enumerate(docs_summary.items(), 1):
            summary_text += f"""{idx}. [{info['category']}] {info['title']}
   출처: {info['source']}
   요약: {info['summary']}

"""

        # Gemini에게 문서 선택 요청
        print(f"\n🤖 Gemini에게 문서 선택 요청 중...")

        prompt = f"""다음은 대학 입시 관련 문서들의 요약본입니다.
사용자의 질문과 관련있는 문서를 선택하세요.

질문: "{rewritten_query}"

문서 목록:
{summary_text}

선택 지침:
1. 질문에 직접적으로 답변할 수 있는 문서만 선택
2. 너무 많이 선택하지 말 것 (보통 2-3개, 최대 5개)
3. 관련 문서 번호만 쉼표로 구분하여 답변 (예: "1, 3, 5")
4. 관련 문서가 전혀 없으면 "없음"이라고만 답변
5. 설명이나 다른 말은 하지 말고 번호만 답변

답변:"""

        try:
            result = await gemini_service.generate(
                prompt,
                system_instruction="당신은 문서 선택 전문가입니다. 번호만 답변하세요."
            )

            print(f"   Gemini 응답: {result.strip()}")

            # "없음" 체크
            if "없음" in result or not result.strip():
                print(f"   ❌ 관련 문서 없음")
                print(f"{'='*80}\n")
                return []

            # 번호 추출
            numbers = re.findall(r'\d+', result)
            selected_files = []

            for num in numbers:
                idx = int(num) - 1
                if 0 <= idx < len(docs_summary):
                    filename = list(docs_summary.keys())[idx]
                    selected_files.append(filename)

            print(f"\n✅ {len(selected_files)}개 문서 선택됨:")
            for filename in selected_files:
                info = docs_summary[filename]
                print(f"   - {info['title']} ({filename})")

            print(f"{'='*80}\n")
            return selected_files

        except Exception as e:
            print(f"⚠️ 문서 선택 실패: {e}")
            print(f"   → 모든 문서 사용")
            print(f"{'='*80}\n")
            return list(docs_summary.keys())

    @staticmethod
    async def get_full_documents(filenames: list[str]) -> tuple[str, str]:
        """
        3단계: 전체 문서 가져오기
        선택된 문서들의 모든 청크를 순서대로 이어붙이기

        Returns:
            (full_text, source): 전체 문서 텍스트와 출처
        """
        print(f"{'='*80}")
        print(f"📄 3단계: 전체 문서 가져오기 (청크 이어붙이기)")
        print(f"{'='*80}")

        client = supabase_service.get_client()
        full_text = ""
        source = ""

        for filename in filenames:
            print(f"📖 문서 처리 중: {filename}")

            # 해당 파일의 모든 청크 가져오기
            response = client.table('policy_documents')\
                .select('content, metadata')\
                .eq('metadata->>fileName', filename)\
                .execute()

            if not response.data:
                print(f"   ⚠️ 청크가 없습니다")
                continue

            # chunkIndex 순서대로 정렬
            chunks = sorted(
                response.data,
                key=lambda x: x.get('metadata', {}).get('chunkIndex', 0)
            )

            # 첫 문서의 출처를 source로 설정
            if not source:
                source = chunks[0].get('metadata', {}).get('source', '공식 문서')

            # 문서 헤더 추가
            title = chunks[0].get('metadata', {}).get('title', filename)
            total_chunks = len(chunks)

            full_text += f"\n\n{'='*60}\n"
            full_text += f"📄 문서: {title}\n"
            full_text += f"{'='*60}\n\n"

            print(f"   청크 수: {total_chunks}개")

            # 모든 청크 이어붙이기
            for chunk in chunks:
                full_text += chunk['content']
                full_text += "\n\n"

            total_chars = sum(len(c['content']) for c in chunks)
            print(f"   총 길이: {total_chars:,}자")

        print(f"\n✅ 전체 문서 길이: {len(full_text):,}자")
        print(f"   출처: {source}")
        print(f"{'='*80}\n")

        return full_text, source

    @staticmethod
    async def generate_answer(rewritten_query: str, full_documents: str) -> str:
        """
        4단계: 답변 생성
        Gemini에게 전체 문서를 전달하고 답변 받기
        """
        print(f"{'='*80}")
        print(f"🤖 4단계: Gemini 답변 생성")
        print(f"{'='*80}")
        print(f"질문: {rewritten_query}")
        print(f"컨텍스트 길이: {len(full_documents):,}자")

        prompt = f"""당신은 대학 입시 전문 상담사입니다.
아래 공식 문서를 **전부 읽고** 학생의 질문에 정확하게 답변하세요.

질문: {rewritten_query}

공식 문서:
{full_documents}

답변 지침:
1. 문서의 내용을 근거로 정확하게 답변할 것
2. 학생이 이해하기 쉽게 친절하고 상세하게 설명할 것
3. 구체적인 수치나 제도를 명확히 인용할 것
4. 문서에 없는 내용은 추측하지 말고 "문서에 해당 내용이 없습니다"라고 안내할 것
5. 중요한 정보는 불렛 포인트로 정리할 것

답변:"""

        try:
            print(f"   Gemini 호출 중...")
            answer = await gemini_service.generate(
                prompt,
                system_instruction="당신은 친절하고 정확한 대학 입시 전문 상담사입니다."
            )

            print(f"✅ 답변 생성 완료 (길이: {len(answer)}자)")
            print(f"{'='*80}\n")

            return answer

        except Exception as e:
            print(f"❌ 답변 생성 실패: {e}")
            print(f"{'='*80}\n")
            raise

    @staticmethod
    async def search_and_answer(user_query: str) -> dict:
        """
        전체 RAG 프로세스 실행

        Returns:
            {
                'found': bool,
                'response': str,
                'source': str,
                'rewritten_query': str
            }
        """
        print(f"\n{'#'*80}")
        print(f"# 🚀 새로운 RAG 시스템 시작")
        print(f"# 원본 질문: {user_query}")
        print(f"{'#'*80}\n")

        try:
            # 1️⃣ Query Rewrite
            rewritten = await RAGServiceV2.rewrite_query(user_query)

            # 2️⃣ 문서 선택
            selected_files = await RAGServiceV2.select_documents(rewritten)

            if not selected_files:
                print(f"❌ 관련 문서가 없습니다 → 일반 모드로 전환\n")
                return {
                    'found': False,
                    'response': '',
                    'source': '',
                    'rewritten_query': rewritten
                }

            # 3️⃣ 전체 문서 가져오기
            full_docs, source = await RAGServiceV2.get_full_documents(selected_files)

            # 4️⃣ 답변 생성
            answer = await RAGServiceV2.generate_answer(rewritten, full_docs)

            print(f"{'#'*80}")
            print(f"# ✅ RAG 프로세스 완료")
            print(f"{'#'*80}\n")

            return {
                'found': True,
                'response': answer,
                'source': source,
                'rewritten_query': rewritten
            }

        except Exception as e:
            print(f"\n{'#'*80}")
            print(f"# ❌ RAG 프로세스 오류: {e}")
            print(f"{'#'*80}\n")
            import traceback
            traceback.print_exc()
            raise


# 전역 인스턴스
rag_service_v2 = RAGServiceV2()
