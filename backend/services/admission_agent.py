"""
대학 입시 데이터 분석 에이전트
Gemini 3.0 Flash Preview와 ScoreConverter 연동
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# .env 파일 로드
try:
    from dotenv import load_dotenv
    # backend 폴더의 .env 파일 찾기
    current_dir = Path(__file__).resolve().parent
    backend_dir = current_dir.parent if current_dir.name == "services" else current_dir
    env_path = backend_dir / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
    else:
        # 상위 디렉토리들에서 .env 찾기
        for parent in [current_dir, *current_dir.parents]:
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ .env 파일 로드됨: {env_path}")
                break
except ImportError:
    print("⚠️  python-dotenv가 설치되지 않았습니다. 환경변수를 직접 설정해주세요.")
except Exception as e:
    print(f"⚠️  .env 파일 로드 중 오류: {e}")

try:
    from backend.services.score_converter import ScoreConverter
    from backend.services.data_standard import (
        korean_std_score_table,
        math_std_score_table,
        social_studies_data,
        science_inquiry_data,
        major_subjects_grade_cuts,
        english_grade_data,
        history_grade_data
    )
except ModuleNotFoundError:
    from score_converter import ScoreConverter
    from data_standard import (
        korean_std_score_table,
        math_std_score_table,
        social_studies_data,
        science_inquiry_data,
        major_subjects_grade_cuts,
        english_grade_data,
        history_grade_data
    )

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai 패키지가 설치되어 있지 않습니다.")
    print("설치: pip install google-generativeai")
    sys.exit(1)


class AdmissionAgent:
    """대학 입시 데이터 분석 에이전트"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Gemini API 키 (None이면 환경변수에서 가져옴)
        """
        # API 키 설정
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY가 설정되지 않았습니다.\n"
                "환경변수로 설정하거나 생성자에 api_key를 전달하세요."
            )
        
        genai.configure(api_key=api_key)
        
        # ScoreConverter 초기화
        self.converter = ScoreConverter()
        
        # 데이터 준비
        self.all_data = self._prepare_all_data()
        
        # Gemini 모델 초기화 (gemini-3-flash-preview)
        self.model = genai.GenerativeModel(
            model_name='gemini-3-flash-preview',
            system_instruction=self._get_system_prompt()
        )
        
        # 채팅 세션 시작
        self.chat = self.model.start_chat(history=[])
    
    def _prepare_all_data(self) -> Dict:
        """모든 데이터를 JSON 직렬화 가능한 형태로 준비"""
        return {
            "국어": {
                "표준점수_테이블": {str(k): v for k, v in korean_std_score_table.items()},
                "선택과목_등급컷": major_subjects_grade_cuts.get("국어", {})
            },
            "수학": {
                "표준점수_테이블": {str(k): v for k, v in math_std_score_table.items()},
                "선택과목_등급컷": major_subjects_grade_cuts.get("수학", {})
            },
            "영어": {
                "등급_데이터": english_grade_data
            },
            "한국사": {
                "등급_데이터": history_grade_data
            },
            "사회탐구": {
                과목: {원점수: 정보 for 원점수, 정보 in 데이터.items()}
                for 과목, 데이터 in social_studies_data.items()
            },
            "과학탐구": {
                과목: {원점수: 정보 for 원점수, 정보 in 데이터.items()}
                for 과목, 데이터 in science_inquiry_data.items()
            }
        }
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return f"""당신은 대학 입시 데이터 분석 전문가입니다.
사용자의 모호한 입력을 '2026 수능 데이터' 기준으로 표준화하고, 팩트 기반의 분석 결과만 제공하세요.

## 가용 데이터
{json.dumps(self.all_data, ensure_ascii=False, indent=2)}

## 1. 입력 데이터 해석 및 정규화 가이드
1. **과목 매핑 및 보정**:
   - "등급 132" -> [국어 1등급, 영어 3등급, 수학 2등급]
   - 과목 미표기 시 일반적 순서(국/수/영/탐1/탐2)를 따름.
   - **선택과목 추론**:
     - 국어 미표기 시 -> [화법과 작문] 가정
     - 수학 미표기 시 -> [확률과 통계] 가정
     - 수학 '확통' 선택 시 -> 탐구는 [사회문화/생활과 윤리]로 가정 (인문계 최다 선택)
     - 수학 '미적/기하' 선택 시 -> 탐구는 [지구과학1/생명과학1]으로 가정 (자연계 최다 선택)

2. **미입력 과목 추정**:
   - 예측/분석을 위해 필요한 경우 국어/수학/영어/탐구1/탐구2 중 점수가 제공되지 않은 과목은 임의로 생성하세요
   - 다른 과목들과 비슷한 백분위를 갖도록 추정하되, 임의로 생성했다는 표기를 명시하세요

## 2. 점수 체계 변환 알고리즘 (Strict Rules)
대학 합격 예측은 정밀해야 하므로 다음 규칙을 엄격히 따르세요:

1. **등급 -> 점수 변환 (보수적 접근)**:
   - 사용자가 '등급'만 제시한 경우, 가용 데이터 표에서 **"해당 등급의 중간 표준점수/백분위"**를 적용하세요.
   - 예: 1등급(4%~0%) 입력 시 -> 백분위 98에 해당하는 표준점수 적용

2. **지표 통일**:
   - 모든 점수는 최종적으로 **'등급 - 백분위 - 표준점수'**의 형태로 변환되어야 합니다.
   - 원점수나 백분위가 입력되면 가용 데이터의 [원점수-표준점수 환산표]를 정확히 참조하세요.

## 3. 응답 형식
사용자의 입력을 분석한 후, 다음 형식으로 응답하세요:

### 입력 해석
- 입력된 정보 요약
- 추정된 선택과목
- 임의로 생성된 과목 (있다면)

### 정규화된 성적
각 과목별로:
- 과목명 (선택과목)
- 등급
- 백분위
- 표준점수

### 분석
- 전반적인 성적 수준
- 강점 과목
- 개선이 필요한 과목
"""
    
    def send_message(self, user_input: str) -> str:
        """
        사용자 메시지 전송 및 응답 받기
        
        Args:
            user_input: 사용자 입력
            
        Returns:
            에이전트 응답
        """
        try:
            response = self.chat.send_message(user_input)
            return response.text
        except Exception as e:
            return f"❌ 오류 발생: {str(e)}"
    
    def convert_score(self, subject: str, **kwargs) -> Optional[Dict]:
        """
        ScoreConverter를 사용한 점수 변환
        
        Args:
            subject: 과목명
            **kwargs: standard_score, percentile, raw_score, elective 등
            
        Returns:
            변환된 점수 정보
        """
        try:
            return self.converter.convert_score(subject, **kwargs)
        except Exception as e:
            print(f"❌ 점수 변환 오류: {e}")
            return None


def interactive_test():
    """터미널 인터랙티브 테스트"""
    print("="*70)
    print("🎓 2026 수능 대학 입시 데이터 분석 에이전트")
    print("="*70)
    print()
    
    # API 키 확인
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print()
        api_key = input("Gemini API 키를 입력하세요 (또는 Enter로 종료): ").strip()
        if not api_key:
            print("종료합니다.")
            return
    
    try:
        agent = AdmissionAgent(api_key=api_key)
        print("✅ 에이전트 초기화 완료")
        print()
        print("💡 사용 예시:")
        print("  - '등급 132' 입력 시 → 국어1/영어3/수학2 해석")
        print("  - '국어 90점 수학 미적분 85점' 입력")
        print("  - '국어 1등급 수학 백분위 95' 입력")
        print()
        print("종료하려면 'exit', 'quit', 'q'를 입력하세요.")
        print("="*70)
        print()
        
        while True:
            try:
                user_input = input("📝 입력: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 종료합니다.")
                    break
                
                print()
                print("🤖 분석 중...")
                print("-"*70)
                
                response = agent.send_message(user_input)
                print(response)
                print("-"*70)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 종료합니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {e}")
                print()
    
    except Exception as e:
        print(f"❌ 에이전트 초기화 실패: {e}")


if __name__ == "__main__":
    interactive_test()
