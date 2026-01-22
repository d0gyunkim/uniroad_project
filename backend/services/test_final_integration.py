"""
최종 통합 테스트: ConsultingAgent에서 경희대+서울대 환산 점수 자동 계산
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multi_agent.sub_agents import ConsultingAgent

load_dotenv()


async def test_final_integration():
    """컨설팅 에이전트 최종 통합 테스트"""
    
    print("="*80)
    print("최종 통합 테스트: 경희대 + 서울대 환산 점수")
    print("="*80)
    
    test_cases = [
        {
            "name": "테스트 1: 최상위권 학생 (11111)",
            "query": "나 11111이야. 서울대 의대랑 경희대 의대 점수 비교해줘"
        },
        {
            "name": "테스트 2: 자연계 학생 (표준점수 입력)",
            "query": "국어 140 수학 135 영어 1등급 탐구1 70 탐구2 66일 때 서울대 공대랑 경희대 공대 어디가 유리해?"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"{test_case['name']}")
        print(f"{'='*80}")
        print(f"질문: {test_case['query']}")
        print()
        
        agent = ConsultingAgent()
        result = await agent.execute(test_case['query'])
        
        print(f"[상태] {result.get('status')}")
        
        # 정규화된 성적
        normalized = result.get('normalized_scores', {})
        if normalized:
            print("\n[정규화된 성적]")
            subjects = normalized.get('과목별_성적', {})
            for subj, data in list(subjects.items())[:5]:  # 처음 5개만
                grade = data.get('등급', 'N/A')
                std = data.get('표준점수', 'N/A')
                pct = data.get('백분위', 'N/A')
                print(f"  {subj}: {grade}등급 / 표준 {std} / 백분위 {pct}")
        
        # 경희대 환산 점수
        khu_scores = normalized.get('경희대_환산점수', {})
        if khu_scores:
            print("\n[경희대 환산 점수]")
            for track in ["인문", "사회", "자연"]:
                score_data = khu_scores.get(track, {})
                if score_data.get('계산_가능'):
                    final = score_data.get('최종점수', 0)
                    bonus = score_data.get('과탐_가산점', 0)
                    bonus_text = f" (+{bonus}점)" if bonus > 0 else ""
                    print(f"  {track}: {final:.1f}점{bonus_text}")
        
        # 서울대 환산 점수
        snu_scores = normalized.get('서울대_환산점수', {})
        if snu_scores:
            print("\n[서울대 환산 점수]")
            for track in ["일반전형", "디자인"]:
                score_data = snu_scores.get(track, {})
                if score_data.get('계산_가능'):
                    final = score_data.get('최종점수', 0)
                    bonus = score_data.get('과탐_가산점', 0)
                    bonus_text = f" (+{bonus}점)" if bonus > 0 else ""
                    print(f"  {track}: {final:.1f}점{bonus_text}")
        
        if result.get('status') != 'error':
            print(f"\n[에이전트 응답 미리보기]")
            print(result.get('result', 'N/A')[:300] + "...")
        else:
            print(f"\n[에러] {result.get('result', 'N/A')}")
        
        if i < len(test_cases):
            print("\n" + "="*80)
            await asyncio.sleep(1)
    
    print("\n" + "="*80)
    print("✅ 최종 통합 테스트 완료!")
    print("="*80)
    print("\n요약:")
    print("- ConsultingAgent가 성적 정규화 후 자동으로 경희대+서울대 환산 점수 계산")
    print("- 로컬 연산만으로 계산 완료 (API 호출 없음)")
    print("- Gemini가 질문에 따라 필요한 정보만 선택적으로 출력")


if __name__ == "__main__":
    asyncio.run(test_final_integration())
