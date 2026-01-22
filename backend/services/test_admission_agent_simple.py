"""
대학 입시 데이터 분석 에이전트 간단 테스트
API 키를 직접 입력하여 빠르게 테스트
"""

import os
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    current_dir = Path(__file__).resolve().parent
    backend_dir = current_dir.parent if current_dir.name == "services" else current_dir
    env_path = backend_dir / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨: {env_path}")
    else:
        for parent in [current_dir, *current_dir.parents]:
            env_path = parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                print(f"✅ .env 파일 로드됨: {env_path}")
                break
except ImportError:
    pass
except Exception as e:
    print(f"⚠️  .env 파일 로드 중 오류: {e}")

try:
    from admission_agent import AdmissionAgent
except ImportError:
    print("❌ admission_agent.py를 찾을 수 없습니다.")
    print("현재 디렉토리에서 실행하세요.")
    exit(1)


def simple_test():
    """간단한 테스트"""
    print("="*70)
    print("🧪 대학 입시 데이터 분석 에이전트 테스트")
    print("="*70)
    print()
    
    # API 키 확인
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        print()
        print("API 키 발급: https://makersuite.google.com/app/apikey")
        print()
        api_key = input("Gemini API 키를 입력하세요 (또는 Enter로 건너뛰기): ").strip()
        print()
    
    if not api_key:
        print("⚠️  API 키 없이 ScoreConverter만 테스트합니다.")
        print()
        test_score_converter_only()
        return
    
    try:
        print("✅ 에이전트 초기화 중...")
        agent = AdmissionAgent(api_key=api_key)
        print("✅ 초기화 완료!")
        print()
        
        # 테스트 케이스들
        test_cases = [
            "등급 132",
            "국어 언어와매체 92점, 수학 미적분 77점",
            "국어 1등급 수학 백분위 95",
        ]
        
        print("="*70)
        print("📋 자동 테스트 케이스")
        print("="*70)
        print()
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"[테스트 {i}] 입력: {test_input}")
            print("-"*70)
            
            try:
                response = agent.send_message(test_input)
                print(response)
            except Exception as e:
                print(f"❌ 오류: {e}")
            
            print("-"*70)
            print()
            
            if i < len(test_cases):
                input("다음 테스트로 진행하려면 Enter를 누르세요...")
                print()
        
        print("="*70)
        print("✅ 자동 테스트 완료!")
        print()
        print("💡 대화형 모드로 전환하려면 'python3 admission_agent.py'를 실행하세요.")
        print("="*70)
        
    except Exception as e:
        print(f"❌ 에이전트 초기화 실패: {e}")
        print()
        print("대신 ScoreConverter만 테스트합니다.")
        print()
        test_score_converter_only()


def test_score_converter_only():
    """ScoreConverter만 테스트"""
    from score_converter import ScoreConverter
    
    print("="*70)
    print("🧮 ScoreConverter 단독 테스트")
    print("="*70)
    print()
    
    converter = ScoreConverter()
    
    test_cases = [
        ("국어", {"raw_score": 92, "elective": "언어와매체"}),
        ("수학", {"raw_score": 77, "elective": "미적분"}),
        ("국어", {"standard_score": 140}),
        ("수학", {"percentile": 95}),
        ("생명과학1", {"standard_score": 70}),
        ("사회문화", {"percentile": 90}),
    ]
    
    for subject, kwargs in test_cases:
        result = converter.convert_score(subject, **kwargs)
        
        input_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        print(f"📝 {subject} ({input_str})")
        
        if result:
            print(f"   표준점수: {result['standard_score']}")
            print(f"   백분위: {result['percentile']}")
            print(f"   등급: {result['grade']}")
            if 'raw_score' in result:
                print(f"   원점수: {result['raw_score']}")
        else:
            print("   ❌ 변환 실패")
        
        print()
    
    print("="*70)
    print("✅ ScoreConverter 테스트 완료!")
    print("="*70)


if __name__ == "__main__":
    simple_test()
