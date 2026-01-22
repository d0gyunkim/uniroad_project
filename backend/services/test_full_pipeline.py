"""
전체 파이프라인 테스트 (Orchestration Agent -> ConsultingAgent)
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# .env 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
print(f"✅ .env 파일 로드됨: {env_path}")

from services.multi_agent.orchestration_agent import run_orchestration_agent

async def test_pipeline():
    """전체 파이프라인 테스트"""
    print("=" * 60)
    print("전체 파이프라인 테스트")
    print("=" * 60)
    
    test_messages = [
        "나 11232야",
        "나 13425인데 표점으로 환산하면 얼마야?",
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n\n테스트 {i}")
        print(f"입력: {message}")
        print("-" * 60)
        
        try:
            result = await run_orchestration_agent(message)
            
            print("\n[Orchestration Agent 결과]")
            print(f"User Intent: {result.get('user_intent')}")
            print(f"\nExecution Plan:")
            for step in result.get('execution_plan', []):
                print(f"  Step {step['step']}: {step['agent']}")
                print(f"    Query: {step['query']}")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
