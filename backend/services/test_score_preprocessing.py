"""
성적 전처리 기능 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from multi_agent.score_preprocessing import (
    extract_grade_from_query,
    normalize_scores,
    format_normalized_scores_text,
    preprocess_scores_for_query,
    normalize_scores_from_extracted,
    format_normalized_scores_for_consulting,
    build_preprocessed_query
)


def test_extract_grade():
    """성적 추출 테스트"""
    print("="*60)
    print("테스트 1: 성적 추출")
    print("="*60)
    
    test_cases = [
        "나 11232야 서울대 갈 수 있어?",
        "국어 140 수학 미적분 130 영어 2등급",
        "국어 1등급 수학 표준점수 143 영어 3등급 탐구1 2등급 탐구2 2등급",
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n[테스트 케이스 {i}]")
        print(f"입력: {query}")
        result = extract_grade_from_query(query)
        print(f"추출된 과목 수: {len(result['subjects'])}개")
        for subject, score_info in result['subjects'].items():
            print(f"  - {subject}: {score_info['type']} {score_info['value']}")
        print(f"선택과목 추론: {result['선택과목_추론']}")


def test_normalize():
    """성적 정규화 테스트"""
    print("\n" + "="*60)
    print("테스트 2: 성적 정규화")
    print("="*60)
    
    query = "나 11232야"
    print(f"\n입력: {query}")
    
    raw_info = extract_grade_from_query(query)
    normalized = normalize_scores(raw_info)
    
    print(f"\n정규화된 과목 수: {len(normalized['과목별_성적'])}개")
    for subject, data in normalized['과목별_성적'].items():
        print(f"\n{subject}:")
        print(f"  등급: {data.get('등급')}")
        print(f"  표준점수: {data.get('표준점수')}")
        print(f"  백분위: {data.get('백분위')}")
        if data.get('추정됨'):
            print(f"  (추정됨)")


def test_format():
    """텍스트 포맷팅 테스트"""
    print("\n" + "="*60)
    print("테스트 3: 텍스트 포맷팅")
    print("="*60)
    
    query = "국어 언매 140 수학 미적 130 영어 2등급 탐구1 60 탐구2 65"
    print(f"\n입력: {query}")
    
    raw_info = extract_grade_from_query(query)
    normalized = normalize_scores(raw_info)
    formatted = format_normalized_scores_text(normalized)
    
    print("\n포맷팅된 결과:")
    print(formatted)


def test_preprocess_for_query():
    """쿼리 전처리 테스트"""
    print("\n" + "="*60)
    print("테스트 4: 쿼리 전처리 (전체 통합)")
    print("="*60)
    
    user_message = "나 11232야 서울대 의대 갈 수 있어?"
    original_query = "2025학년도 입결 기준 서울대 의예과 합격 가능성 분석"
    
    print(f"\n사용자 메시지: {user_message}")
    print(f"원본 쿼리: {original_query}")
    
    final_query = preprocess_scores_for_query(user_message, original_query)
    
    print("\n전처리된 최종 쿼리:")
    print("-" * 60)
    print(final_query)
    print("-" * 60)


def test_no_scores():
    """성적이 없는 경우 테스트"""
    print("\n" + "="*60)
    print("테스트 5: 성적 정보 없는 경우")
    print("="*60)
    
    user_message = "서울대 의대 입결 어떻게 돼?"
    original_query = "서울대 의예과 입결 정보 제공"
    
    print(f"\n사용자 메시지: {user_message}")
    print(f"원본 쿼리: {original_query}")
    
    final_query = preprocess_scores_for_query(user_message, original_query)
    
    print("\n결과:")
    if final_query == original_query:
        print("✅ 성적 정보 없음 - 원본 쿼리 그대로 반환")
    else:
        print("❌ 예상치 못한 변경 발생")
    print(f"쿼리: {final_query}")


def test_normalize_from_extracted():
    """LLM 추출 성적 정규화 테스트 (신규 기능)"""
    print("\n" + "="*60)
    print("테스트 6: LLM 추출 성적 정규화 (normalize_scores_from_extracted)")
    print("="*60)
    
    # LLM이 추출한 성적 시뮬레이션
    extracted_scores = {
        "국어": {"type": "등급", "value": 1, "선택과목": "화법과작문"},
        "수학": {"type": "등급", "value": 1, "선택과목": "확률과통계"},
        "영어": {"type": "등급", "value": 2},
        "생활과윤리": {"type": "등급", "value": 3},
        "사회문화": {"type": "등급", "value": 2}
    }
    
    print(f"\n입력 (LLM 추출 성적):")
    for subject, info in extracted_scores.items():
        print(f"  - {subject}: {info}")
    
    normalized = normalize_scores_from_extracted(extracted_scores)
    
    print(f"\n정규화 결과:")
    for subject, data in normalized["과목별_성적"].items():
        print(f"\n{subject}:")
        print(f"  등급: {data.get('등급')}")
        print(f"  표준점수: {data.get('표준점수')}")
        print(f"  백분위: {data.get('백분위')}")
        if data.get('선택과목'):
            print(f"  선택과목: {data.get('선택과목')}")


def test_format_for_consulting():
    """컨설팅 agent용 포맷팅 테스트 (영어는 등급만)"""
    print("\n" + "="*60)
    print("테스트 7: 컨설팅 agent용 포맷팅 (영어는 등급만)")
    print("="*60)
    
    extracted_scores = {
        "국어": {"type": "등급", "value": 1, "선택과목": "화법과작문"},
        "수학": {"type": "표준점수", "value": 140, "선택과목": "미적분"},
        "영어": {"type": "등급", "value": 2},
        "생명과학1": {"type": "등급", "value": 2},
        "지구과학1": {"type": "등급", "value": 3}
    }
    
    print(f"\n입력 (자연계 학생 시뮬레이션):")
    for subject, info in extracted_scores.items():
        print(f"  - {subject}: {info}")
    
    normalized = normalize_scores_from_extracted(extracted_scores)
    formatted = format_normalized_scores_for_consulting(normalized)
    
    print("\n포맷팅 결과:")
    print(formatted)
    
    # 영어에 백분위가 없는지 확인
    if "백분위" in formatted.split("영어")[1].split("\n")[0]:
        print("\n❌ 오류: 영어에 백분위가 포함됨!")
    else:
        print("\n✅ 영어는 등급만 표시됨")


def test_build_preprocessed_query():
    """최종 쿼리 생성 테스트"""
    print("\n" + "="*60)
    print("테스트 8: 최종 쿼리 생성 (build_preprocessed_query)")
    print("="*60)
    
    extracted_scores = {
        "국어": {"type": "등급", "value": 1, "선택과목": "화법과작문"},
        "수학": {"type": "등급", "value": 1, "선택과목": "확률과통계"},
        "영어": {"type": "등급", "value": 2},
        "생활과윤리": {"type": "등급", "value": 3},
        "사회문화": {"type": "등급", "value": 2}
    }
    
    original_query = "2025학년도 입결 기준 서울대 의예과 합격 가능성 분석"
    
    print(f"\n입력:")
    print(f"  extracted_scores: {len(extracted_scores)}개 과목")
    print(f"  원본 쿼리: {original_query}")
    
    final_query = build_preprocessed_query(extracted_scores, original_query)
    
    print("\n최종 쿼리:")
    print("-" * 60)
    print(final_query)
    print("-" * 60)


def test_science_track():
    """자연계 학생 테스트"""
    print("\n" + "="*60)
    print("테스트 9: 자연계 학생 시뮬레이션")
    print("="*60)
    
    # 자연계 학생: 미적분 + 과학탐구
    extracted_scores = {
        "국어": {"type": "등급", "value": 2, "선택과목": "언어와매체"},
        "수학": {"type": "표준점수", "value": 145, "선택과목": "미적분"},
        "영어": {"type": "등급", "value": 1},
        "물리학1": {"type": "표준점수", "value": 68},
        "화학1": {"type": "표준점수", "value": 70}
    }
    
    print(f"\n입력 (자연계 학생 - 미적분, 물리1+화학1):")
    for subject, info in extracted_scores.items():
        print(f"  - {subject}: {info}")
    
    normalized = normalize_scores_from_extracted(extracted_scores)
    formatted = format_normalized_scores_for_consulting(normalized)
    
    print("\n포맷팅 결과:")
    print(formatted)


if __name__ == "__main__":
    print("\n🚀 성적 전처리 기능 테스트 시작\n")
    
    try:
        test_extract_grade()
        test_normalize()
        test_format()
        test_preprocess_for_query()
        test_no_scores()
        
        # 신규 테스트 (LLM 구조화 기반)
        test_normalize_from_extracted()
        test_format_for_consulting()
        test_build_preprocessed_query()
        test_science_track()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
