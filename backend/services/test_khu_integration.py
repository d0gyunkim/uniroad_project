"""
경희대 환산 점수 통합 테스트
ConsultingAgent가 성적을 정규화하고 경희대 환산 점수를 자동 계산하는지 검증
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multi_agent.sub_agents import ConsultingAgent

load_dotenv()


async def test_consulting_agent_with_khu_score():
    """컨설팅 에이전트 경희대 환산 점수 테스트"""
    
    print("="*80)
    print("경희대 환산 점수 통합 테스트")
    print("="*80)
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "테스트 1: 표준 입력 (11211 형식)",
            "query": "나 11211이야. 경희대 의대 갈 수 있어?"
        },
        {
            "name": "테스트 2: 표준점수로 입력",
            "query": "국어 표준점수 140, 수학 표준점수 128, 영어 2등급, 탐구1 백분위 99, 탐구2 백분위 95일 때 경희대 환산 점수 알려줘"
        },
        {
            "name": "테스트 3: 표준점수만 궁금한 경우",
            "query": "나 13425야. 내 표준점수 뭐야?"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"{test_case['name']}")
        print(f"{'='*80}")
        print(f"질문: {test_case['query']}")
        print()
        
        # 컨설팅 에이전트 실행
        agent = ConsultingAgent()
        result = await agent.execute(test_case['query'])
        
        # 결과 확인
        print(f"\n[상태] {result.get('status')}")
        
        # 정규화된 성적 확인
        normalized = result.get('normalized_scores', {})
        if normalized:
            print("\n[정규화된 성적]")
            subjects = normalized.get('과목별_성적', {})
            for subj, data in subjects.items():
                grade = data.get('등급', 'N/A')
                std = data.get('표준점수', 'N/A')
                pct = data.get('백분위', 'N/A')
                print(f"  {subj}: {grade}등급 / 표준점수 {std} / 백분위 {pct}")
        
        # 경희대 환산 점수 확인
        khu_scores = normalized.get('경희대_환산점수', {})
        if khu_scores:
            print("\n[경희대 환산 점수]")
            for track, score_data in khu_scores.items():
                if score_data.get('계산_가능'):
                    final = score_data.get('최종점수', 0)
                    bonus = score_data.get('과탐_가산점', 0)
                    bonus_text = f" (과탐가산 +{bonus}점)" if bonus > 0 else ""
                    print(f"  {track}: {final:.1f}점{bonus_text}")
                else:
                    print(f"  {track}: 계산 불가 ({score_data.get('오류', 'Unknown')})")
        
        # 에이전트 응답 확인
        print(f"\n[에이전트 응답]")
        print(result.get('result', 'N/A')[:500])  # 처음 500자만
        
        if i < len(test_cases):
            print("\n" + "="*80)
            await asyncio.sleep(1)  # API 레이트 리밋 방지
    
    print("\n" + "="*80)
    print("테스트 완료!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_consulting_agent_with_khu_score())
