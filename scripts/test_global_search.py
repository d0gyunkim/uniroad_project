"""
전역 검색 모드 테스트 스크립트
라우팅 없는 전역 검색 기능을 테스트합니다.
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

# 전역 변수로 초기화 상태 관리
_initialized = False
_rag_system = None

def main():
    """메인 함수"""
    global _initialized, _rag_system
    
    if not _initialized:
        print("=" * 60)
        print("🔍 전역 검색 모드 테스트 (라우팅 없음)")
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
        
        # RAG 시스템 초기화
        print("\n📦 RAG 시스템 초기화 중...")
        try:
            _rag_system = RAGSystem()
            print("✅ RAG 시스템 초기화 완료")
        except Exception as e:
            print(f"❌ RAG 시스템 초기화 실패: {str(e)}")
            import traceback
            print(traceback.format_exc())
            sys.exit(1)
        
        _initialized = True
    
    rag_system = _rag_system
    
    # 테스트 질문
    school_name = "고려대학교"
    test_queries = [
        "수시 전형 모집인원"]
    
    print(f"\n📋 테스트 학교: {school_name}")
    print(f"📝 테스트 질문 수: {len(test_queries)}개\n")
    
    for idx, query in enumerate(test_queries, 1):
        print("=" * 60)
        print(f"질문 {idx}: {query}")
        print("=" * 60)
        
        try:
            # 전역 검색 수행
            results = rag_system.search_global_raw(
                school_name=school_name,
                query=query,
                top_k=10
            )
            
            if not results:
                print("⚠️  검색 결과가 없습니다.\n")
                continue
            
            print(f"\n✅ 검색 완료: {len(results)}개 청크 발견\n")
            
            # 상위 10개 청크 내용 출력
            top_results = results[:10]
            
            for i, result in enumerate(top_results, 1):
                print("─" * 60)
                print(f"📄 청크 #{i}")
                print("─" * 60)
                
                # 청크 ID
                chunk_id = result.get('chunk_id', 'N/A')
                print(f"ID: {chunk_id}")
                
                # 페이지 번호
                page_number = result.get('page_number', 'N/A')
                print(f"페이지: {page_number}")
                
                # 유사도 점수
                score = result.get('score', 0.0)
                print(f"유사도 점수: {score:.4f}")
                
                # 청크 타입
                chunk_type = result.get('chunk_type', 'N/A')
                print(f"청크 타입: {chunk_type}")
                
                # 섹션 제목 (있는 경우)
                section_title = result.get('section_title')
                if section_title:
                    print(f"섹션: {section_title}")
                
                # 청크 내용
                content = result.get('content', '')
                print(f"\n내용:")
                print("-" * 60)
                # 내용이 너무 길면 일부만 표시
                if len(content) > 500:
                    print(content[:500] + "...")
                    print(f"\n[내용 길이: {len(content)}자, 앞부분 500자만 표시]")
                else:
                    print(content)
                
                print()
            
            print("=" * 60)
            print(f"총 {len(results)}개 청크 중 상위 {len(top_results)}개 표시")
            print("=" * 60)
            
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

