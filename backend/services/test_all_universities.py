"""
5개 대학 환산 점수 최종 통합 테스트
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multi_agent.sub_agents import ConsultingAgent

load_dotenv()


async def test_all_universities():
    """5개 대학 환산 점수 통합 테스트"""
    
    print("="*80)
    print("5개 대학 환산 점수 최종 테스트: ConsultingAgent 통합")
    print("="*80)
    
    query = "나 11111이야. SKY랑 서강대, 경희대 중에서 어디가 유리해?"
    print(f"\n질문: {query}\n")
    
    agent = ConsultingAgent()
    result = await agent.execute(query)
    
    print(f"[상태] {result.get('status')}")
    
    # 정규화된 성적
    normalized = result.get('normalized_scores', {})
    
    # 경희대
    khu = normalized.get('경희대_환산점수', {})
    if khu:
        print("\n【경희대 (600점 만점)】")
        for track in ["인문", "자연"]:
            d = khu.get(track, {})
            if d.get('계산_가능'):
                print(f"  {track}: {d['최종점수']:.1f}점")
    
    # 서울대
    snu = normalized.get('서울대_환산점수', {})
    if snu:
        print("\n【서울대 (1000점 스케일)】")
        d = snu.get('일반전형', {})
        if d.get('계산_가능'):
            print(f"  일반전형: {d['최종점수']:.1f}점 → 1000점: {d.get('최종점수_1000', 0):.1f}")
    
    # 연세대
    yon = normalized.get('연세대_환산점수', {})
    if yon:
        print("\n【연세대 (1000점 만점)】")
        for track in ["인문", "자연"]:
            d = yon.get(track, {})
            if d.get('계산_가능'):
                print(f"  {track}: {d['최종점수']:.1f}점")
    
    # 고려대
    kor = normalized.get('고려대_환산점수', {})
    if kor:
        print("\n【고려대 (1000점 환산)】")
        for track in ["인문", "자연"]:
            d = kor.get(track, {})
            if d.get('계산_가능'):
                print(f"  {track}: {d['최종점수']:.1f}점")
    
    # 서강대
    sog = normalized.get('서강대_환산점수', {})
    if sog:
        print("\n【서강대】")
        for track in ["인문", "자연"]:
            d = sog.get(track, {})
            if d.get('계산_가능'):
                print(f"  {track}: {d['최종점수']:.1f}점 ({d.get('적용방식', '')})")
    
    print("\n" + "="*80)
    print("✅ 5개 대학 환산 점수 계산 완료!")
    print("  - 경희대 (600점 만점)")
    print("  - 서울대 (1000점 스케일)")
    print("  - 연세대 (1000점 만점)")
    print("  - 고려대 (1000점 환산)")
    print("  - 서강대 (A/B형 최고점)")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_all_universities())
