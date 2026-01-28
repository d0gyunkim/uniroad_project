"""
Supabase 기반 RAG 시스템 테스트 스크립트
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
load_dotenv(override=True)

from core.rag_system import RAGSystem

def main():
    """메인 함수"""
    print("=" * 60)
    print("🔍 Supabase 기반 RAG 시스템 테스트")
    print("=" * 60)
    
    # 환경 변수 확인
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요.")
        sys.exit(1)
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 GEMINI_API_KEY를 설정하세요.")
        sys.exit(1)
    
    print("\n✅ 환경 변수 확인 완료")
    print(f"   Supabase URL: {supabase_url[:30]}...")
    print(f"   Gemini API Key: {gemini_key[:10]}...")
    
    # RAG 시스템 초기화
    print("\n📦 RAG 시스템 초기화 중...")
    try:
        rag_system = RAGSystem()
        print("✅ RAG 시스템 초기화 완료")
    except Exception as e:
        print(f"❌ RAG 시스템 초기화 실패: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
    
    # 테스트 질문
    school_name = "고려대학교"
    test_questions = [
        "고려대학교 수시 전형은 어떻게 되나요?",
        "학생부종합 전형의 모집인원은 얼마나 되나요?",
        "수능 최저학력기준이 있나요?",
    ]
    
    print(f"\n📋 테스트 학교: {school_name}")
    print(f"📝 테스트 질문 수: {len(test_questions)}개\n")
    
    for idx, question in enumerate(test_questions, 1):
        print("=" * 60)
        print(f"질문 {idx}: {question}")
        print("=" * 60)
        
        try:
            # 답변 생성 (스트리밍 모드)
            print("\n💬 답변 생성 중...\n")
            answer_parts = []
            for chunk in rag_system.answer(
                question=question,
                school_name=school_name,
                conversation_history=[],
                stream=True
            ):
                answer_parts.append(chunk)
                print(chunk, end="", flush=True)
            
            answer = "".join(answer_parts)
            print("\n\n✅ 답변 생성 완료")
            
            # 일반 모드로도 테스트
            print("\n" + "-" * 60)
            print("일반 모드 테스트:")
            print("-" * 60)
            result = rag_system.answer(
                question=question,
                school_name=school_name,
                conversation_history=[],
                stream=False
            )
            
            if isinstance(result, dict):
                print(f"\n📊 선택된 섹션 수: {len(result.get('selected_sections', []))}")
                print(f"📄 근거 문서 수: {len(result.get('evidence', []))}")
                if result.get('thinking_process'):
                    print(f"\n🧠 사고 과정:\n{result['thinking_process'][:200]}...")
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        print("\n")
    
    print("=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()

