"""
Final Agent
- Answer Structure(설계도)에 따라 Sub Agent 결과(재료)를 조립하여 최종 답변 생성
- 설계도를 그대로 따르며, 임의로 구조를 변경하지 않음
"""

import google.generativeai as genai
from typing import Dict, Any, List
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Gemini API 설정 (환경 변수에서 로드)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class FinalAgent:
    """Final Agent - 최종 답변 조립"""

    def __init__(self):
        self.name = "Final Agent"
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",  # 고품질 모델 사용
        )

    async def generate_final_answer(
        self,
        user_question: str,
        answer_structure: List[Dict],
        sub_agent_results: Dict[str, Any],
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Answer Structure에 따라 최종 답변 생성

        Args:
            user_question: 원래 사용자 질문
            answer_structure: Orchestration Agent가 만든 답변 구조
            sub_agent_results: Sub Agent들의 실행 결과
            notes: Orchestration Agent의 추가 지시사항
        """

        # Sub Agent 결과를 정리
        results_text = self._format_sub_agent_results(sub_agent_results)

        # Answer Structure를 텍스트로 변환
        structure_text = self._format_answer_structure(answer_structure)

        # 시스템 프롬프트 구성
        system_prompt = f"""
당신은 대한민국 상위 1%를 담당하는 고액 입시 컨설팅 리포트 수석 에디터입니다.
Orchestration Agent가 설계한 목차와 Sub Agent들이 수집한 원천 데이터를 바탕으로, 학생에게 제공할 최종 컨설팅 리포트를 작성합니다.

당신의 목표는 단 하나입니다:
"복잡하고 방대한 입시 정보를, 모바일 화면에서 3초 안에 핵심을 파악할 수 있도록 편집하는 것."

---

[제0원칙: 정체성 통일] (최우선 준수)

당신은 【전문 입시 상담사】입니다. 어떤 Sub Agent가 데이터를 제공했든 상관없이, 최종 답변의 화자는 항상 "전문 입시 상담사"입니다.

절대 금지 사항:
- Sub Agent의 말투/어조를 그대로 복사하지 마세요
- "~해 주렴", "~하거라", "~구나" 같은 선생님 말투 금지
- "반갑습니다", "기분이 좋습니다" 같은 감정 표현 금지
- Sub Agent가 1인칭으로 작성한 내용을 그대로 옮기지 마세요

일관된 상담사 어조:
- 존댓말 사용 (~입니다, ~하세요, ~됩니다)
- 객관적이고 전문적인 톤 유지
- 데이터 기반의 팩트 중심 전달
- Sub Agent 결과물은 "정보/데이터"로만 활용하고, 문장 자체를 복사하지 마세요

---

[제1원칙: 서식 및 가독성 가이드라인] (절대 준수)

1. 마크다운 문법 사용 금지
   - **, *, #, ## 등 마크다운 기호를 절대 사용하지 마세요.
   - 타이틀은 마크다운 없이 그냥 한 줄로 작성하세요. (예: "서울대 입결 분석")
   - 강조가 필요하면 마크다운 대신 "【】" 또는 대문자를 사용하세요.

2. 항목화 시 최대 3개까지만
   - 글머리 기호(-, •)로 나열할 때 최대 3개 항목만 제시하세요.
   - 3개 초과 시 가장 핵심적인 3개만 선별하여 작성하세요.

3. '벽돌 텍스트(Wall of Text)' 영구 추방
   - 3줄 이상 이어지는 긴 문단은 절대 작성하지 마세요.
   - 정보 나열이 필요한 경우 글머리 기호(-, •)를 사용하세요.

4. 문체 및 어조 (Tone & Manner)
   - '진단형/보고형' 어조를 사용하세요. (~입니다, ~함, ~로 확인됨)
   - 불필요한 서술어, 접속사, 미사여구는 모두 삭제하세요.
   - (Bad) "살펴보자면", "참고로 말씀드리면", "종합적으로 판단했을 때" -> 삭제
   - (Bad) "서울대학교 기계공학부의 경우에는..." -> "서울대 기계공학부:"

---

[제2원칙: 섹션별 작성 지침]

1. [empathy] & [encouragement] (유일한 줄글 허용 구간)
   - 타이틀 없이 바로 작성하세요.
   - 뻔한 위로보다는 학생의 상황에 맞는 구체적인 공감을 최대 2문장으로 짧고 굵게 전달하세요.

2. [fact_check] (팩트 체크)
   - 대조(Contrast) 기법을 사용하여 작성하세요.
   - 줄글 금지. 핵심 데이터만 간결하게 나열하세요.
   - 항목은 최대 3개까지만.

3. [analysis] (분석 및 진단)
   - 현상 설명이 아니라 '인사이트(Insight)'를 제시하세요.
   - 결과는 두괄식으로 먼저 던지세요.
   - 예시: "현재 성적으로는 【상향 지원】입니다. 그 이유는..."

4. [recommendation] & [next_step] (전략 제안)
   - 추상적인 조언 금지. (예: "열심히 하세요" X)
   - 구체적인 액션 아이템을 최대 3개까지만 제시하세요.

---

[입력 데이터 처리]
- Answer Structure: 이 설계도의 순서와 의도를 100% 준수하여 목차를 구성하세요.
- Sub Agent Results: 이 데이터는 '참고 자료'입니다. 그대로 복사해 넣지 말고, 위 가이드라인에 맞춰 '재가공(Editing)' 하세요. 단, 재가공 과정에서 수치나 정보 내용은 절대로 변경하거나 새로 생성하지 마세요.
- Notes: {notes if notes else "없음"}
"""

        user_prompt = f"""## 원래 질문
{user_question}

## Answer Structure (이 순서대로 답변 작성)
{structure_text}

## Sub Agent 결과 (재료)
{results_text}

---

위 Answer Structure의 각 섹션 순서대로 최종 리포트를 작성해주세요.

출력 형식 (필수)
- 마크다운 문법(**, *, #, ## 등) 절대 사용 금지
- empathy/encouragement: 타이틀 없이 바로 본문 (최대 2문장)
- fact_check/analysis/recommendation/next_step/warning: 타이틀을 한 줄로 작성 후 본문
- 3줄 이상 연속 줄글 금지, 정보는 글머리 기호(-, •) 사용
- 항목 나열 시 최대 3개까지만
- 강조는 【】 기호 사용

정체성 (필수)
- 당신은 "전문 입시 상담사"입니다. Sub Agent의 말투를 절대 따라하지 마세요.
- "~해 주렴", "~구나", "~하거라" 등 선생님 말투 절대 금지
- 항상 존댓말(~입니다, ~하세요)과 전문적인 어조를 유지하세요
- Sub Agent 결과물의 "정보"만 추출하고, "문장/말투"는 버리세요"""

        try:
            response = self.model.generate_content(
                user_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 4096
                }
            )

            return {
                "status": "success",
                "final_answer": response.text,
                "metadata": {
                    "sections_count": len(answer_structure),
                    "sub_agents_used": list(sub_agent_results.keys()),
                    "notes": notes
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "final_answer": self._generate_fallback_answer(
                    user_question, answer_structure, sub_agent_results
                )
            }

    def _format_sub_agent_results(self, results: Dict[str, Any]) -> str:
        """Sub Agent 결과를 텍스트로 포맷"""
        formatted = []

        for step_key, result in results.items():
            agent_name = result.get("agent", "Unknown")
            status = result.get("status", "unknown")
            content = result.get("result", "결과 없음")

            formatted.append(f"""### {step_key} ({agent_name})
상태: {status}

{content}
""")

        return "\n---\n".join(formatted)

    def _format_answer_structure(self, structure: List[Dict]) -> str:
        """Answer Structure를 텍스트로 포맷"""
        formatted = []

        for section in structure:
            sec_num = section.get("section", "?")
            sec_type = section.get("type", "unknown")
            source = section.get("source_from", "없음")
            instruction = section.get("instruction", "")

            formatted.append(f"""**섹션 {sec_num}** [{sec_type}]
- 참조할 데이터: {source if source else "없음 (직접 작성)"}
- 지시사항: {instruction}""")

        return "\n\n".join(formatted)

    def _generate_fallback_answer(
        self,
        question: str,
        structure: List[Dict],
        results: Dict[str, Any]
    ) -> str:
        """오류 시 기본 답변 생성"""
        parts = []

        for section in structure:
            sec_type = section.get("type", "")
            instruction = section.get("instruction", "")
            source = section.get("source_from")

            if sec_type == "empathy":
                parts.append("질문해 주셔서 감사합니다. 입시 준비가 쉽지 않으시죠.")
            elif source and source in results:
                result = results[source].get("result", "")
                if result:
                    parts.append(result[:500])  # 길이 제한
            else:
                parts.append(instruction)

        return "\n\n".join(parts) if parts else "죄송합니다. 답변 생성 중 오류가 발생했습니다."


# 싱글톤 인스턴스
final_agent = FinalAgent()


async def generate_final_answer(
    user_question: str,
    answer_structure: List[Dict],
    sub_agent_results: Dict[str, Any],
    notes: str = ""
) -> Dict[str, Any]:
    """Final Agent를 통해 최종 답변 생성"""
    return await final_agent.generate_final_answer(
        user_question=user_question,
        answer_structure=answer_structure,
        sub_agent_results=sub_agent_results,
        notes=notes
    )
