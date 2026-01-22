"""
원점수 변환 기능 테스트
"""

try:
    from backend.services.score_converter import ScoreConverter
except ModuleNotFoundError:
    from score_converter import ScoreConverter


def test_raw_score_conversion():
    converter = ScoreConverter()
    
    print("="*60)
    print("원점수 변환 기능 테스트")
    print("="*60)
    
    # 테스트 케이스
    test_cases = [
        # (과목, 선택과목, 원점수, 설명)
        ("국어", "화법과작문", 100, "만점"),
        ("국어", "화법과작문", 90, "1등급컷"),
        ("국어", "화법과작문", 87, "1-2등급 사이"),
        ("국어", "화법과작문", 83, "2등급컷"),
        ("국어", "언어와매체", 100, "만점"),
        ("국어", "언어와매체", 85, "1등급컷"),
        ("국어", "언어와매체", 92, "만점-1등급 사이"),
        ("수학", "확률과통계", 100, "만점"),
        ("수학", "확률과통계", 87, "1등급컷"),
        ("수학", "확률과통계", 85, "1-2등급 사이"),
        ("수학", "미적분", 100, "만점"),
        ("수학", "미적분", 85, "1등급컷"),
        ("수학", "미적분", 77, "2-3등급 사이"),
        ("수학", "미적분", 10, "8등급컷"),
        ("수학", "기하", 100, "만점"),
        ("수학", "기하", 85, "1등급컷"),
        ("수학", "기하", 70, "3-4등급 사이"),
    ]
    
    for subject, elective, raw_score, description in test_cases:
        result = converter.convert_score(subject, raw_score=raw_score, elective=elective)
        
        print(f"\n{subject} {elective} {raw_score}점 ({description})")
        if result:
            print(f"  표준점수: {result['standard_score']}")
            print(f"  백분위: {result['percentile']}")
            print(f"  등급: {result['grade']}")
        else:
            print("  ❌ 변환 실패")
    
    # 에러 케이스 테스트
    print("\n" + "="*60)
    print("에러 케이스 테스트")
    print("="*60)
    
    # 선택과목 없이 원점수 입력
    print("\n1. 선택과목 없이 원점수 입력")
    try:
        converter.convert_score("국어", raw_score=90)
        print("  ❌ 에러가 발생하지 않음")
    except ValueError as e:
        print(f"  ✅ 예상된 에러: {e}")
    
    # 존재하지 않는 선택과목
    print("\n2. 존재하지 않는 선택과목")
    result = converter.convert_score("국어", raw_score=90, elective="존재하지않음")
    if result is None:
        print("  ✅ None 반환")
    else:
        print(f"  ❌ 예상치 못한 결과: {result}")
    
    # 탐구 과목에 원점수 입력
    print("\n3. 탐구 과목에 원점수 입력")
    result = converter.convert_score("생명과학1", raw_score=45, elective="없음")
    if result is None:
        print("  ✅ None 반환 (탐구 과목은 원점수 조회 불가)")
    else:
        print(f"  ❌ 예상치 못한 결과: {result}")
    
    print("\n" + "="*60)
    print("테스트 완료")
    print("="*60)


if __name__ == "__main__":
    test_raw_score_conversion()
