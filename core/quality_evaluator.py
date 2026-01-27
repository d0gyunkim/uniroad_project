"""
품질 평가 모듈
답변의 품질을 평가하여 적절한지 판단
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import config


class QualityEvaluator:
    """답변 품질 평가를 담당하는 클래스"""
    
    def __init__(self, model_name: str = None):
        """
        초기화
        
        Args:
            model_name: LLM 모델명
        """
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
    
    def evaluate(self, question: str, answer: str) -> dict:
        """
        답변의 품질을 평가
        
        Args:
            question: 사용자 질문
            answer: 생성된 답변
            
        Returns:
            {
                "is_acceptable": bool,
                "evaluation_text": str
            }
        """
        evaluation_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 컨설턴트의 답변 품질을 평가하는 전문가입니다.

**평가 기준:**
1. **관련성** (0-10점): 답변이 질문과 직접적으로 관련이 있는가?
2. **완전성** (0-10점): 질문에 대한 답변이 충분히 완전한가? (중요 정보 누락 없음)
3. **정확성** (0-10점): 답변에 구체적인 정보(숫자, 날짜, 이름 등)가 포함되어 있는가?
4. **유용성** (0-10점): 학생/학부모에게 실제로 도움이 되는 답변인가?

**불합격 기준 (다음 중 하나라도 해당되면 불합격):**
- "찾을 수 없습니다", "정보가 없습니다" 같은 불완전한 답변
- 질문과 관련 없는 답변
- 구체적인 정보 없이 추상적인 설명만 있는 답변
- 총점이 30점 미만인 경우

**평가 형식:**
총점: [0-40점]
판정: [합격/불합격]
이유: [간단한 평가 이유]

---
**질문:**
{question}

**답변:**
{answer}

---
**평가:**
""")
        
        llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0)
        chain = evaluation_prompt | llm | StrOutputParser()
        
        evaluation = chain.invoke({"question": question, "answer": answer})
        is_acceptable = "불합격" not in evaluation and "합격" in evaluation
        
        return {
            "is_acceptable": is_acceptable,
            "evaluation_text": evaluation
        }

