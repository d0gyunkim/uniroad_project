"""
경희대 + 서울대 환산 점수 통합 테스트
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.khu_score_calculator import calculate_khu_score
from services.snu_score_calculator import calculate_snu_score

# 테스트 데이터: 최상위권 학생 (국어 140, 수학 135, 영어 1등급, 탐구 70/66)
test_data = {
    "과목별_성적": {
        "국어": {"등급": 1, "표준점수": 140, "백분위": 99},
        "수학": {"등급": 1, "표준점수": 135, "백분위": 99},
        "영어": {"등급": 1, "백분위": 97},
        "한국사": {"등급": 1},
        "탐구1": {"등급": 1, "표준점수": 70, "백분위": 99},
        "탐구2": {"등급": 1, "표준점수": 66, "백분위": 95}
    },
    "선택과목": {
        "국어": "언어와매체",
        "수학": "미적분",
        "탐구_추론": "자연계 (물리학1/화학1)"
    }
}

print("="*80)
print("대학별 환산 점수 비교 (국어 140, 수학 135, 영어 1등급, 탐구 70/66)")
print("="*80)

# 경희대
print("\n【경희대 2026 환산 점수 (600점 만점)】")
khu_scores = calculate_khu_score(test_data)
for track, data in khu_scores.items():
    if data["계산_가능"]:
        final = data["최종점수"]
        bonus = data.get("과탐_가산점", 0)
        bonus_text = f" (과탐가산 +{bonus}점)" if bonus > 0 else ""
        print(f"  {track:10s}: {final:6.1f}점{bonus_text}")

# 서울대
print("\n【서울대 2026 환산 점수】")
snu_scores = calculate_snu_score(test_data)

# 주요 모집단위
main_tracks = ["일반전형", "순수미술", "디자인", "체육교육"]
for track in main_tracks:
    data = snu_scores.get(track, {})
    if data.get("계산_가능"):
        final = data["최종점수"]
        bonus = data.get("과탐_가산점", 0)
        bonus_text = f" (과탐가산 +{bonus}점)" if bonus > 0 else ""
        
        track_name = track if track == "일반전형" else data.get('모집단위', track).split(" - ")[-1]
        print(f"  {track_name:10s}: {final:6.1f}점{bonus_text}")

# 음악대학
print(f"  {'음악대학':10s}:", end="")
music_parts = []
for track in ["성악", "작곡", "음악학"]:
    data = snu_scores.get(track, {})
    if data.get("계산_가능"):
        final = data["최종점수"]
        music_parts.append(f"{track} {final:.1f}점")
print(f" {', '.join(music_parts)}")

print("\n" + "="*80)
print("특징 비교")
print("="*80)
print("【경희대】")
print("  - 600점 만점 체계")
print("  - 계열별 가중치 (인문: 국40%+수25%+탐35%, 자연: 국25%+수40%+탐35%)")
print("  - 자연계 과탐 가산점 과목당 +4점 (총 +8점)")
print("  - 영어/한국사 감점제")
print()
print("【서울대】")
print("  - 일반전형: 수학 1.2배, 탐구 0.8배")
print("  - 과탐 가산점: I+II 조합 +3점, II+II 조합 +5점")
print("  - 모집단위별 상이한 감점제")
print("  - 음악대학: 특수 환산 공식 적용")

print("\n" + "="*80)
print("✅ 대학별 환산 점수 계산 완료!")
print("="*80)
