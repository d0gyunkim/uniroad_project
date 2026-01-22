"""
컨설팅 Agent 간단 테스트 스크립트
"""

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
except:
    pass

# 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.multi_agent.sub_agents import ConsultingAgent


def test():
    """점수 변환 테스트"""
    
    print("="*70)
    print("🧪 컨설팅 Agent 점수 변환 테스트")
    print("="*70)
    
    agent = ConsultingAgent()
    
    # 테스트 케이스
    test_queries = [
        "나 13425야",
        "등급 132",
        "국어 언어와매체 92점 수학 미적분 77점",
        "국어 1등급 수학 표준점수 130 영어 2등급",
        "영어 2등급",  # 영어 단독 테스트
        "수학 표준점수 130",  # 수학 표준점수 단독 테스트
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"[테스트 {i}] 입력: {query}")
        print("="*70)
        
        # 성적 추출
        raw_info = agent._extract_grade_from_query(query)
        print(f"\n📝 추출된 과목: {list(raw_info.get('subjects', {}).keys())}")
        
        # 정규화
        normalized = agent._normalize_scores(raw_info)
        
        # 포맷팅
        formatted = agent._format_normalized_scores(normalized)
        print(f"\n📋 정규화된 성적:")
        print(formatted)
        
        # 평균 백분위
        avg_pct = agent._calculate_average_percentile(normalized)
        if avg_pct:
            print(f"\n📈 평균 백분위: {avg_pct:.1f}")
    
    print("\n" + "="*70)
    print("✅ 테스트 완료!")
    print("="*70)


if __name__ == "__main__":
    test()
