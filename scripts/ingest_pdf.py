"""
PDF 수집 및 Supabase 업로드 스크립트
로컬 PDF 파일을 처리하여 Supabase에 업로드하는 스크립트
"""
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import TOCProcessor, SectionPreprocessor, upload_to_supabase
import config

# ============================================
# 설정: 테스트 폴더 경로
# ============================================
TEST_FOLDER = "테스트_폴더"
SCHOOL_FOLDERS = ["경희대", "고려대", "서울대"]
SCHOOL_NAME_MAP = {
    "경희대": "경희대학교",
    "고려대": "고려대학교",
    "서울대": "서울대학교"
}
# ============================================


def find_pdf_files():
    """
    테스트 폴더에서 모든 PDF 파일을 찾아 반환
    
    Returns:
        [(pdf_path, school_name), ...] 리스트
    """
    pdf_files = []
    test_folder_path = os.path.join(project_root, TEST_FOLDER)
    
    for school_folder in SCHOOL_FOLDERS:
        school_path = os.path.join(test_folder_path, school_folder)
        if not os.path.exists(school_path):
            continue
        
        # 해당 폴더의 모든 PDF 파일 찾기
        pdf_pattern = os.path.join(school_path, "*.pdf")
        found_pdfs = glob(pdf_pattern)
        
        school_name = SCHOOL_NAME_MAP.get(school_folder, school_folder)
        for pdf_path in found_pdfs:
            pdf_files.append((pdf_path, school_name))
    
    return pdf_files


def process_pdf(pdf_path: str, school_name: str) -> dict:
    """
    PDF를 처리하여 processed_data 딕셔너리를 생성
    목차가 감지되지 않으면 None을 반환
    
    Args:
        pdf_path: PDF 파일 경로 (절대 경로)
        school_name: 학교 이름
        
    Returns:
        {
            "sections": 섹션 리스트,
            "chunks": 모든 청크 Document 리스트
        } 또는 None (목차가 없을 경우)
    """
    print(f"\n📄 PDF 처리 시작: {os.path.basename(pdf_path)}")
    print(f"   학교: {school_name}")
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    # 모델 초기화
    model_name = config.DEFAULT_LLM_MODEL
    toc_processor = TOCProcessor(model_name)
    preprocessor = SectionPreprocessor(model_name)
    
    # 1단계: 목차 페이지 감지
    print("   [1단계] 🔍 목차 페이지 감지 중...")
    toc_pages = toc_processor.detect_toc_pages(pdf_path)
    
    if not toc_pages:
        print("   ⚠️  목차 페이지를 찾을 수 없습니다. 이 문서를 건너뜁니다.")
        return None
    
    print(f"   ✅ 목차 페이지 발견: {[p+1 for p in toc_pages]}")
    
    # 2단계: 목차 구조 파싱
    print("   [2단계] 📋 목차 구조 파싱 중...")
    sections = toc_processor.parse_toc_structure(pdf_path, toc_pages)
    
    if not sections:
        print("   ⚠️  목차 파싱 실패. 이 문서를 건너뜁니다.")
        return None
    
    # 3단계: 페이지 범위 검증
    print("   [3단계] ✅ 페이지 범위 검증 중...")
    sections = toc_processor.validate_and_fix_sections(sections, pdf_path)
    print(f"   ✅ {len(sections)}개 섹션 추출 완료")
    
    # 4단계: 병렬 전처리
    print(f"   [4단계] 📄 {len(sections)}개 섹션 병렬 전처리 중... (표 구조 인식 및 임베딩 생성)")
    
    section_data = {}
    all_chunks = []
    
    def process_section(section):
        """섹션 전처리 함수 (병렬 실행용)"""
        section_key = f"{section['start_page']}_{section['end_page']}"
        result = preprocessor.preprocess_section(section, pdf_path)
        return {
            "section_key": section_key,
            "result": result,
            "section": section
        }
    
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_section = {
            executor.submit(process_section, section): idx
            for idx, section in enumerate(sections, 1)
        }
        
        completed = 0
        total = len(sections)
        
        for future in as_completed(future_to_section):
            idx = future_to_section[future]
            try:
                data = future.result()
                
                if not data:
                    print(f"   ❌ 섹션 {idx} 처리 중 오류: 결과가 None입니다")
                    continue
                
                section_key = data.get("section_key", f"section_{idx}")
                result = data.get("result", {})
                section = data.get("section", {"title": f"섹션 {idx}"})
                
                if not result:
                    result = {
                        "vectorstore": None,
                        "documents": [],
                        "table_count": 0
                    }
                
                section_data[section_key] = {
                    "vectorstore": result.get("vectorstore"),
                    "documents": result.get("documents", []),
                    "section": section,
                    "table_count": result.get("table_count", 0)
                }
                
                # 모든 청크 수집
                documents = result.get("documents", [])
                all_chunks.extend(documents)
                
                completed += 1
                table_count = result.get("table_count", 0)
                table_info = f" (표 {table_count}개)" if table_count > 0 else ""
                section_title = section.get("title", f"섹션 {idx}")
                print(f"   ✅ {completed}/{total} 완료: '{section_title}'{table_info} ({len(documents)}개 청크)")
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"   ❌ 섹션 {idx} 처리 중 상세 오류:\n{error_details}")
                completed += 1
    
    print(f"   🎉 모든 섹션 전처리 완료! ({len(sections)}개 섹션, 총 {len(all_chunks)}개 청크)")
    
    # processed_data 딕셔너리 생성
    processed_data = {
        "toc_sections": sections,
        "chunks": all_chunks
    }
    
    return processed_data


def process_and_upload_pdf(pdf_path: str, school_name: str):
    """
    단일 PDF를 처리하고 업로드하는 함수
    
    Args:
        pdf_path: PDF 파일 경로 (절대 경로)
        school_name: 학교 이름
        
    Returns:
        (성공 여부, 문서 ID 또는 None, 건너뛰기 여부)
    """
    try:
        # PDF 처리
        processed_data = process_pdf(pdf_path, school_name)
        
        # 목차가 없으면 건너뛰기
        if processed_data is None:
            return (False, None, True)
        
        # Supabase 업로드
        print(f"   [5단계] 📤 Supabase에 데이터 업로드 중...")
        print(f"   섹션 수: {len(processed_data['toc_sections'])}개")
        print(f"   청크 수: {len(processed_data['chunks'])}개")
        
        document_id = upload_to_supabase(
            school_name=school_name,
            file_path=pdf_path,
            processed_data=processed_data
        )
        
        if document_id:
            print(f"   🎉 업로드 완료! 문서 ID: {document_id}")
            return (True, document_id, False)
        else:
            print(f"   ❌ 업로드 실패")
            return (False, None, False)
            
    except Exception as e:
        import traceback
        print(f"   ❌ 오류 발생: {str(e)}")
        print(f"   상세 오류:\n{traceback.format_exc()}")
        return (False, None, False)


def main():
    """메인 함수"""
    print("=" * 60)
    print("📑 PDF 수집 및 Supabase 업로드 스크립트 (병렬 처리)")
    print("=" * 60)
    
    # PDF 파일 찾기
    print(f"\n📂 PDF 파일 검색 중...")
    pdf_files = find_pdf_files()
    
    if not pdf_files:
        print("❌ 처리할 PDF 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    print(f"✅ 총 {len(pdf_files)}개의 PDF 파일 발견")
    for pdf_path, school_name in pdf_files:
        print(f"   - {os.path.basename(pdf_path)} ({school_name})")
    
    # 결과 추적
    success_count = 0
    failed_count = 0
    skipped_files = []
    uploaded_docs = []
    
    # 병렬 처리
    print(f"\n🚀 병렬 처리 시작...")
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        future_to_pdf = {
            executor.submit(process_and_upload_pdf, pdf_path, school_name): (pdf_path, school_name)
            for pdf_path, school_name in pdf_files
        }
        
        for future in as_completed(future_to_pdf):
            pdf_path, school_name = future_to_pdf[future]
            try:
                success, doc_id, skipped = future.result()
                
                if skipped:
                    skipped_files.append((pdf_path, school_name))
                elif success:
                    success_count += 1
                    uploaded_docs.append((os.path.basename(pdf_path), school_name, doc_id))
                else:
                    failed_count += 1
                    
            except Exception as e:
                import traceback
                print(f"\n❌ {os.path.basename(pdf_path)} 처리 중 예외 발생:")
                print(traceback.format_exc())
                failed_count += 1
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("📊 처리 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {success_count}개")
    print(f"❌ 실패: {failed_count}개")
    print(f"⏭️  건너뜀: {len(skipped_files)}개")
    
    if uploaded_docs:
        print(f"\n📤 업로드된 문서:")
        for filename, school, doc_id in uploaded_docs:
            print(f"   ✅ {filename} ({school}) - ID: {doc_id}")
    
    if skipped_files:
        print(f"\n⏭️  건너뛴 문서 (목차 미감지):")
        for pdf_path, school_name in skipped_files:
            print(f"   - {os.path.basename(pdf_path)} ({school_name})")
    
    if failed_count > 0:
        print(f"\n⚠️  일부 문서 처리에 실패했습니다.")
        sys.exit(1)
    
    print(f"\n🎉 모든 처리 완료!")


if __name__ == "__main__":
    main()

