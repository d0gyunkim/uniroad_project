"""
성적 추출 및 정규화 테스트
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.multi_agent.sub_agents import ConsultingAgent
import json

def test_score_extraction():
    """성적 추출 테스트"""
    print("=" * 60)
    print("성적 추출 테스트")
    print("=" * 60)
    
    agent = ConsultingAgent()
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "Orchestration Agent 출력 (탐구1, 탐구2 명시)",
            "query": "국어 1등급, 수학 1등급, 영어 2등급, 탐구1 3등급, 탐구2 2등급일 때의 예상 표준점수대 산출"
        },
        {
            "name": "구식 출력 (탐구만 명시)",
            "query": "국어 1등급, 수학 1등급, 영어 2등급, 탐구 3등급, 탐구 2등급일 때의 예상 표준점수대 산출"
        },
        {
            "name": "단순 입력",
            "query": "나 11232야"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n\n테스트 {i}: {test['name']}")
        print(f"입력: {test['query']}")
        print("-" * 60)
        
        # 성적 추출
        raw_info = agent._extract_grade_from_query(test['query'])
        print(f"\n추출된 원본 성적:")
        print(json.dumps(raw_info, ensure_ascii=False, indent=2))
        
        # 정규화
        normalized = agent._normalize_scores(raw_info)
        print(f"\n정규화된 성적:")
        print(json.dumps(normalized, ensure_ascii=False, indent=2))
        
        # 포맷팅
        formatted = agent._format_normalized_scores(normalized)
        print(f"\n포맷팅된 출력:")
        print(formatted)
        print("\n" + "=" * 60)

if __name__ == "__main__":
    test_score_extraction()
