"""
2026 수능 점수 변환 사용 예제
"""

try:
    from backend.services.score_converter import ScoreConverter
except ModuleNotFoundError:
    from score_converter import ScoreConverter


def main():
    # ScoreConverter 인스턴스 생성
    converter = ScoreConverter()
    
    print("=" * 60)
    print("2026 수능 점수 변환기")
    print("=" * 60)
    
    # 예제 1: 국어 표준점수로 조회
    print("\n[예제 1] 국어 표준점수 140")
    result = converter.convert_score("국어", standard_score=140)
    if result:
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 2: 수학 백분위로 조회
    print("\n[예제 2] 수학 백분위 90")
    result = converter.convert_score("수학", percentile=90)
    if result:
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 3: 생명과학1 표준점수로 조회
    print("\n[예제 3] 생명과학1 표준점수 65")
    result = converter.convert_score("생명과학1", standard_score=65)
    if result:
        print(f"  - 원점수: {result.get('raw_score', 'N/A')}")
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 4: 사회문화 백분위로 조회
    print("\n[예제 4] 사회문화 백분위 85")
    result = converter.convert_score("사회문화", percentile=85)
    if result:
        print(f"  - 원점수: {result.get('raw_score', 'N/A')}")
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 5: 정확한 값이 없을 때 가장 가까운 값 찾기
    print("\n[예제 5] 물리학1 표준점수 64 (정확한 값 없음)")
    result = converter.convert_score("물리학1", standard_score=64, use_closest=True)
    if result:
        print(f"  - 원점수: {result.get('raw_score', 'N/A')}")
        print(f"  - 표준점수: {result['standard_score']} (가장 가까운 값)")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 6: 원점수로 조회 (국어/수학)
    print("\n[예제 6] 원점수로 조회 - 국어 화법과작문 95점")
    result = converter.convert_score("국어", raw_score=95, elective="화법과작문")
    if result:
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    print("\n[예제 7] 원점수로 조회 - 수학 기하 70점")
    result = converter.convert_score("수학", raw_score=70, elective="기하")
    if result:
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 8: 등급컷 정확히 맞는 경우
    print("\n[예제 8] 등급컷 정확히 맞는 경우 - 수학 확률과통계 87점 (1등급컷)")
    result = converter.convert_score("수학", raw_score=87, elective="확률과통계")
    if result:
        print(f"  - 표준점수: {result['standard_score']}")
        print(f"  - 백분위: {result['percentile']}")
        print(f"  - 등급: {result['grade']}")
    
    # 예제 9: 여러 과목 일괄 조회
    print("\n[예제 9] 여러 과목 일괄 조회")
    subjects_scores = [
        ("국어", 135, None, None, None),
        ("수학", None, 88, None, None),
        ("사회문화", 60, None, None, None),
        ("생명과학1", None, 95, None, None),
        ("국어", None, None, 88, "언어와매체"),
        ("수학", None, None, 75, "미적분")
    ]
    
    for subject, std_score, perc, raw, elective in subjects_scores:
        if std_score:
            result = converter.convert_score(subject, standard_score=std_score)
            input_type = f"표준점수 {std_score}"
        elif perc:
            result = converter.convert_score(subject, percentile=perc)
            input_type = f"백분위 {perc}"
        else:
            result = converter.convert_score(subject, raw_score=raw, elective=elective)
            input_type = f"원점수 {raw}({elective})"
        
        if result:
            print(f"  {subject} ({input_type}): 표준점수={result['standard_score']}, 백분위={result['percentile']}, 등급={result['grade']}")
    
    # 사용 가능한 과목 목록 출력
    print("\n" + "=" * 60)
    print("사용 가능한 과목 목록")
    print("=" * 60)
    subjects = converter.get_available_subjects()
    for category, subject_list in subjects.items():
        print(f"\n[{category}]")
        for i, subject in enumerate(subject_list, 1):
            print(f"  {i}. {subject}")


if __name__ == "__main__":
    main()
