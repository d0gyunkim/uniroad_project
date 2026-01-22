"""
컨설팅 Agent 테스트 스크립트
점수 변환 기능 검증
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent.parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드됨")
except Exception as e:
    print(f"⚠️  .env 파일 로드 오류: {e}")

# 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.multi_agent.sub_agents import ConsultingAgent


async def test_consulting_agent():
    """컨설팅 Agent 테스트"""
    
    print("="*70)
    print("🧪 컨설팅 Agent 점수 변환 테스트")
    print("="*70)
    print()
    
    agent = ConsultingAgent()
    
    # 테스트 케이스
    test_queries = [
        "나 13425야",  # 국어1 수학3 영어4 탐구2 탐구5
        "등급 132",  # 국어1 영어3 수학2
        "국어 언어와매체 92점 수학 미적분 77점",
        "국어 1등급 수학 표준점수 130 영어 2등급",
        "국어 백분위 95 수학 백분위 90",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"[테스트 {i}] 입력: {query}")
        print("="*70)
        
        # 성적 추출 테스트
        raw_info = agent._extract_grade_from_query(query)
        print(f"\n📝 추출된 원본 성적:")
        print(json.dumps(raw_info, ensure_ascii=False, indent=2))
        
        # 정규화 테스트
        normalized = agent._normalize_scores(raw_info)
        print(f"\n📊 정규화된 성적:")
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
        
        # 포맷팅 테스트
        formatted = agent._format_normalized_scores(normalized)
        print(f"\n📋 포맷팅된 성적:")
        print(formatted)
        
        # 평균 백분위
        avg_pct = agent._calculate_average_percentile(normalized)
        print(f"\n📈 평균 백분위: {avg_pct}")
        
        print()
        input("다음 테스트를 계속하려면 Enter를 누르세요...")
    
    print("\n" + "="*70)
    print("✅ 모든 테스트 완료!")
    print("="*70)


async def test_full_execute():
    """전체 execute 테스트 (Gemini API 호출 포함)"""
    
    print("="*70)
    print("🧪 컨설팅 Agent 전체 실행 테스트")
    print("="*70)
    print()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다.")
        return
    
    agent = ConsultingAgent()
    
    test_query = "나 13425야. 어디 갈 수 있어?"
    
    print(f"📝 테스트 입력: {test_query}")
    print("-"*70)
    
    result = await agent.execute(test_query)
    
    print("\n📊 결과:")
    print(f"Status: {result.get('status')}")
    print(f"\n정규화된 성적:")
    print(json.dumps(result.get('normalized_scores', {}), ensure_ascii=False, indent=2))
    print(f"\n분석 결과:")
    print(result.get('result', 'N/A'))
    
    print("\n" + "="*70)
    print("✅ 전체 실행 테스트 완료!")
    print("="*70)


if __name__ == "__main__":
    print("1. 점수 변환만 테스트 (API 호출 없음)")
    print("2. 전체 실행 테스트 (API 호출 포함)")
    
    choice = input("\n선택 (1 또는 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_full_execute())
    else:
        asyncio.run(test_consulting_agent())
