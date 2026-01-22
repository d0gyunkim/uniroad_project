"""
자동 테스트 스크립트 - 에이전트 응답 확인
"""

import os
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    current_dir = Path(__file__).resolve().parent
    backend_dir = current_dir.parent
    env_path = backend_dir / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
        print()
except Exception as e:
    print(f"⚠️  .env 파일 로드 중 오류: {e}")

from admission_agent import AdmissionAgent

def main():
    print("="*70)
    print("🧪 대학 입시 데이터 분석 에이전트 자동 테스트")
    print("="*70)
    print()
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY를 찾을 수 없습니다.")
        return
    
    print("✅ API 키 발견")
    print("✅ 에이전트 초기화 중...")
    
    try:
        agent = AdmissionAgent(api_key=api_key)
        print("✅ 초기화 완료!")
        print()
        
        # 테스트 케이스
        test_input = "등급 132"
        
        print(f"📝 테스트 입력: {test_input}")
        print("-"*70)
        print()
        
        response = agent.send_message(test_input)
        print(response)
        
        print()
        print("-"*70)
        print("✅ 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
