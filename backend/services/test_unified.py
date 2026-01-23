"""
통합 테스트 환경
Orchestration Agent, Sub Agent, Final Integration 테스트를 한 곳에서 실행
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# 경로 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# .env 로드
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from services.multi_agent.orchestration_agent import run_orchestration_agent
from services.multi_agent.sub_agents import ConsultingAgent


class Colors:
    """터미널 색상 코드"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str):
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_section(text: str):
    """섹션 출력"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{text}{Colors.END}")
    print(f"{Colors.YELLOW}{'-'*80}{Colors.END}")


def print_success(text: str):
    """성공 메시지"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """에러 메시지"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """정보 메시지"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def clear_screen():
    """화면 클리어"""
    os.system('clear' if os.name != 'nt' else 'cls')


async def test_orchestration_agent():
    """1. Orchestration Agent 테스트"""
    clear_screen()
    print_header("🎯 Orchestration Agent 테스트")
    
    test_messages = [
        "나 11232야",
        "나 13425인데 표점으로 환산하면 얼마야?",
        "서울대 의예과 모집요강 알려줘",
    ]
    
    print_info("Orchestration Agent는 사용자 질문을 분석하고 실행 계획을 수립합니다.")
    print()
    
    # 테스트 케이스 선택
    print("테스트 케이스:")
    for i, msg in enumerate(test_messages, 1):
        print(f"  {i}. {msg}")
    print(f"  {len(test_messages) + 1}. 직접 입력")
    print()
    
    choice = input("선택 (1-4, Enter=1): ").strip()
    
    if not choice:
        choice = "1"
    
    if choice.isdigit() and 1 <= int(choice) <= len(test_messages):
        message = test_messages[int(choice) - 1]
    elif choice == str(len(test_messages) + 1):
        message = input("\n질문을 입력하세요: ").strip()
        if not message:
            print_error("질문이 입력되지 않았습니다.")
            return
    else:
        print_error("잘못된 선택입니다.")
        return
    
    print_section(f"입력: {message}")
    
    try:
        result = await run_orchestration_agent(message)
        
        print_section("📊 분석 결과")
        print(f"\n{Colors.BOLD}사용자 의도:{Colors.END} {result.get('user_intent')}")
        
        print(f"\n{Colors.BOLD}실행 계획:{Colors.END}")
        for step in result.get('execution_plan', []):
            print(f"  {Colors.GREEN}Step {step['step']}{Colors.END}: {Colors.CYAN}{step['agent']}{Colors.END}")
            print(f"    Query: {step['query']}")
        
        print(f"\n{Colors.BOLD}답변 구조:{Colors.END}")
        answer_structure = result.get('answer_structure', [])
        if isinstance(answer_structure, list):
            for i, section in enumerate(answer_structure, 1):
                print(f"  {i}. {section}")
        elif isinstance(answer_structure, dict):
            for key, value in answer_structure.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {answer_structure}")
        
        print_success("테스트 완료!")
        
    except Exception as e:
        print_error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n\nEnter를 눌러 메인 메뉴로 돌아가기...")


async def test_consulting_agent():
    """2. Consulting Agent 테스트"""
    clear_screen()
    print_header("📊 Consulting Agent 테스트 (점수 변환 & 정규화)")
    
    test_queries = [
        "나 13425야",
        "등급 132",
        "국어 언어와매체 92점 수학 미적분 77점",
        "국어 1등급 수학 표준점수 130 영어 2등급",
        "국어 백분위 95 수학 백분위 90",
    ]
    
    print_info("Consulting Agent는 성적을 정규화하고 대학별 환산 점수를 계산합니다.")
    print()
    
    # 테스트 케이스 선택
    print("테스트 케이스:")
    for i, query in enumerate(test_queries, 1):
        print(f"  {i}. {query}")
    print(f"  {len(test_queries) + 1}. 직접 입력")
    print()
    
    choice = input("선택 (1-6, Enter=1): ").strip()
    
    if not choice:
        choice = "1"
    
    if choice.isdigit() and 1 <= int(choice) <= len(test_queries):
        query = test_queries[int(choice) - 1]
    elif choice == str(len(test_queries) + 1):
        query = input("\n성적을 입력하세요: ").strip()
        if not query:
            print_error("성적이 입력되지 않았습니다.")
            return
    else:
        print_error("잘못된 선택입니다.")
        return
    
    print_section(f"입력: {query}")
    
    agent = ConsultingAgent()
    
    # 1. 성적 추출
    print_section("1️⃣ 성적 추출")
    raw_info = agent._extract_grade_from_query(query)
    print(f"\n추출된 과목: {Colors.CYAN}{', '.join(raw_info.get('subjects', {}).keys())}{Colors.END}")
    
    # 2. 정규화
    print_section("2️⃣ 성적 정규화")
    normalized = agent._normalize_scores(raw_info)
    
    # 과목별 성적
    subjects = normalized.get('과목별_성적', {})
    if subjects:
        print(f"\n{Colors.BOLD}과목별 성적:{Colors.END}")
        for subj, data in subjects.items():
            grade = data.get('등급', 'N/A')
            std = data.get('표준점수', 'N/A')
            pct = data.get('백분위', 'N/A')
            print(f"  {subj:8s}: {grade}등급 / 표준 {std} / 백분위 {pct}")
    
    # 평균 백분위
    avg_pct = agent._calculate_average_percentile(normalized)
    if avg_pct:
        print(f"\n{Colors.BOLD}평균 백분위:{Colors.END} {Colors.GREEN}{avg_pct:.1f}{Colors.END}")
    
    # 3. 대학별 환산 점수
    print_section("3️⃣ 대학별 환산 점수 계산 중...")
    
    # 환산 점수 계산 (ConsultingAgent의 execute 로직과 동일)
    from services.khu_score_calculator import calculate_khu_score
    from services.snu_score_calculator import calculate_snu_score
    from services.yonsei_score_calculator import calculate_yonsei_score
    from services.korea_score_calculator import calculate_korea_score
    from services.sogang_score_calculator import calculate_sogang_score
    
    khu_scores = calculate_khu_score(normalized)
    normalized['경희대_환산점수'] = khu_scores
    
    snu_scores = calculate_snu_score(normalized)
    normalized['서울대_환산점수'] = snu_scores
    
    yonsei_scores = calculate_yonsei_score(normalized)
    normalized['연세대_환산점수'] = yonsei_scores
    
    korea_scores = calculate_korea_score(normalized)
    normalized['고려대_환산점수'] = korea_scores
    
    sogang_scores = calculate_sogang_score(normalized)
    normalized['서강대_환산점수'] = sogang_scores
    
    # 경희대
    khu_scores = normalized.get('경희대_환산점수', {})
    if khu_scores:
        print(f"\n{Colors.BOLD}【경희대 (600점 만점)】{Colors.END}")
        for track in ["인문", "사회", "자연", "예술체육"]:
            score_data = khu_scores.get(track, {})
            if score_data.get('계산_가능'):
                final = score_data.get('최종점수', 0)
                bonus = score_data.get('과탐_가산점', 0)
                bonus_text = f" (과탐가산 +{bonus}점)" if bonus > 0 else ""
                print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END}{bonus_text}")
    
    # 서울대
    snu_scores = normalized.get('서울대_환산점수', {})
    if snu_scores:
        print(f"\n{Colors.BOLD}【서울대】{Colors.END}")
        for track in ["일반전형", "디자인", "체육교육"]:
            score_data = snu_scores.get(track, {})
            if score_data.get('계산_가능'):
                final = score_data.get('최종점수', 0)
                final_1000 = score_data.get('최종점수_1000', final)
                bonus = score_data.get('과탐_가산점', 0)
                bonus_text = f" (과탐가산 +{bonus}점)" if bonus > 0 else ""
                print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END} (1000점 스케일: {final_1000:.1f}){bonus_text}")
    
    # 연세대
    yon_scores = normalized.get('연세대_환산점수', {})
    if yon_scores:
        print(f"\n{Colors.BOLD}【연세대 (1000점 만점)】{Colors.END}")
        for track in ["인문", "자연"]:
            score_data = yon_scores.get(track, {})
            if score_data.get('계산_가능'):
                final = score_data.get('최종점수', 0)
                print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END}")
    
    # 고려대
    kor_scores = normalized.get('고려대_환산점수', {})
    if kor_scores:
        print(f"\n{Colors.BOLD}【고려대 (1000점 환산)】{Colors.END}")
        for track in ["인문", "자연"]:
            score_data = kor_scores.get(track, {})
            if score_data.get('계산_가능'):
                final = score_data.get('최종점수', 0)
                print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END}")
    
    # 서강대
    sog_scores = normalized.get('서강대_환산점수', {})
    if sog_scores:
        print(f"\n{Colors.BOLD}【서강대】{Colors.END}")
        for track in ["인문", "자연"]:
            score_data = sog_scores.get(track, {})
            if score_data.get('계산_가능'):
                final = score_data.get('최종점수', 0)
                method = score_data.get('적용방식', '')
                print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END} ({method})")
    
    print_success("\n테스트 완료!")
    
    input("\n\nEnter를 눌러 메인 메뉴로 돌아가기...")


async def test_final_integration():
    """3. Final Integration 테스트 (전체 파이프라인)"""
    clear_screen()
    print_header("🚀 Final Integration 테스트 (전체 파이프라인)")
    
    test_cases = [
        {
            "name": "최상위권 학생 (11111)",
            "query": "나 11111이야. 서울대 의대랑 경희대 의대 점수 비교해줘"
        },
        {
            "name": "자연계 학생 (표준점수 입력)",
            "query": "국어 140 수학 135 영어 1등급 탐구1 70 탐구2 66일 때 서울대 공대랑 경희대 공대 어디가 유리해?"
        },
        {
            "name": "SKY 비교",
            "query": "나 11111이야. SKY랑 서강대, 경희대 중에서 어디가 유리해?"
        }
    ]
    
    print_info("전체 파이프라인: ConsultingAgent 실행 + Gemini API 호출")
    print()
    
    # API 키 확인
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print_error("GEMINI_API_KEY가 설정되지 않았습니다.")
        input("\n\nEnter를 눌러 메인 메뉴로 돌아가기...")
        return
    
    # 테스트 케이스 선택
    print("테스트 케이스:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. {case['name']}")
        print(f"     {Colors.CYAN}{case['query']}{Colors.END}")
    print(f"  {len(test_cases) + 1}. 직접 입력")
    print()
    
    choice = input("선택 (1-4, Enter=1): ").strip()
    
    if not choice:
        choice = "1"
    
    if choice.isdigit() and 1 <= int(choice) <= len(test_cases):
        test_case = test_cases[int(choice) - 1]
        query = test_case['query']
        print(f"\n{Colors.BOLD}테스트:{Colors.END} {test_case['name']}")
    elif choice == str(len(test_cases) + 1):
        query = input("\n질문을 입력하세요: ").strip()
        if not query:
            print_error("질문이 입력되지 않았습니다.")
            return
    else:
        print_error("잘못된 선택입니다.")
        return
    
    print_section(f"질문: {query}")
    
    try:
        agent = ConsultingAgent()
        result = await agent.execute(query)
        
        print_section("📊 실행 결과")
        print(f"\n{Colors.BOLD}상태:{Colors.END} {result.get('status')}")
        
        # 정규화된 성적
        normalized = result.get('normalized_scores', {})
        if normalized:
            subjects = normalized.get('과목별_성적', {})
            if subjects:
                print(f"\n{Colors.BOLD}정규화된 성적:{Colors.END}")
                for subj, data in list(subjects.items())[:5]:  # 처음 5개만
                    grade = data.get('등급', 'N/A')
                    std = data.get('표준점수', 'N/A')
                    pct = data.get('백분위', 'N/A')
                    print(f"  {subj}: {grade}등급 / 표준 {std} / 백분위 {pct}")
            
            # 경희대 환산 점수
            khu_scores = normalized.get('경희대_환산점수', {})
            if khu_scores:
                print(f"\n{Colors.BOLD}경희대 환산 점수:{Colors.END}")
                for track in ["인문", "자연"]:
                    score_data = khu_scores.get(track, {})
                    if score_data.get('계산_가능'):
                        final = score_data.get('최종점수', 0)
                        bonus = score_data.get('과탐_가산점', 0)
                        bonus_text = f" (+{bonus}점)" if bonus > 0 else ""
                        print(f"  {track}: {Colors.GREEN}{final:.1f}점{Colors.END}{bonus_text}")
            
            # 서울대 환산 점수
            snu_scores = normalized.get('서울대_환산점수', {})
            if snu_scores:
                print(f"\n{Colors.BOLD}서울대 환산 점수:{Colors.END}")
                score_data = snu_scores.get("일반전형", {})
                if score_data.get('계산_가능'):
                    final = score_data.get('최종점수', 0)
                    final_1000 = score_data.get('최종점수_1000', final)
                    bonus = score_data.get('과탐_가산점', 0)
                    bonus_text = f" (+{bonus}점)" if bonus > 0 else ""
                    print(f"  일반전형: {Colors.GREEN}{final:.1f}점{Colors.END} (1000점: {final_1000:.1f}){bonus_text}")
        
        # Gemini 응답
        print_section("🤖 Gemini 응답")
        response = result.get('result', 'N/A')
        if len(response) > 500:
            print(response[:500] + f"\n{Colors.YELLOW}... (총 {len(response)}자){Colors.END}")
        else:
            print(response)
        
        print_success("\n테스트 완료!")
        
    except Exception as e:
        print_error(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n\nEnter를 눌러 메인 메뉴로 돌아가기...")


async def main_menu():
    """메인 메뉴"""
    while True:
        clear_screen()
        print_header("🧪 UniZ 통합 테스트 환경")
        
        print(f"{Colors.BOLD}테스트 메뉴:{Colors.END}\n")
        print(f"  {Colors.CYAN}1{Colors.END}. 🎯 Orchestration Agent 테스트")
        print(f"     {Colors.YELLOW}└─{Colors.END} 사용자 질문 분석 & 실행 계획 수립")
        print()
        print(f"  {Colors.CYAN}2{Colors.END}. 📊 Consulting Agent 테스트")
        print(f"     {Colors.YELLOW}└─{Colors.END} 점수 변환, 정규화, 대학별 환산 점수")
        print()
        print(f"  {Colors.CYAN}3{Colors.END}. 🚀 Final Integration 테스트")
        print(f"     {Colors.YELLOW}└─{Colors.END} 전체 파이프라인 (Gemini API 포함)")
        print()
        print(f"  {Colors.RED}Q{Colors.END}. 종료")
        print()
        
        choice = input("선택 (1-3, Q): ").strip().upper()
        
        if choice == '1':
            await test_orchestration_agent()
        elif choice == '2':
            await test_consulting_agent()
        elif choice == '3':
            await test_final_integration()
        elif choice == 'Q':
            clear_screen()
            print_success("테스트를 종료합니다.")
            break
        else:
            print_error("잘못된 선택입니다.")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        clear_screen()
        print_info("\n테스트가 중단되었습니다.")
    except Exception as e:
        print_error(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
