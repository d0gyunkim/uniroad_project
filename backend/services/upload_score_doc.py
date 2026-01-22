"""
표준점수 산출 방식 문서를 Supabase에 업로드
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from services.supabase_client import SupabaseService

# .env 로드
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
print(f"✅ .env 파일 로드됨: {env_path}")

def upload_score_calculation_pdf():
    """표준점수 산출 방식 PDF를 Supabase에 업로드"""
    
    # PDF 파일 경로
    pdf_path = os.path.join(
        os.path.dirname(__file__),
        "docs",
        "score_calculation_method.pdf"
    )
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return None
    
    # 파일 크기 확인
    file_size = os.path.getsize(pdf_path)
    print(f"\n📄 업로드할 파일:")
    print(f"   경로: {pdf_path}")
    print(f"   크기: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # PDF 읽기
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Supabase Storage에 업로드
    print(f"\n⬆️  Supabase Storage에 업로드 중...")
    result = SupabaseService.upload_pdf_to_storage(
        file_bytes=pdf_bytes,
        file_name="유니로드_표준점수_및_백분위_산출_방식.pdf"
    )
    
    if result:
        storage_file_name, public_url = result
        print(f"\n✅ 업로드 완료!")
        print(f"\n📊 결과:")
        print(f"   Storage 파일명: {storage_file_name}")
        print(f"   Public URL: {public_url}")
        print(f"\n💡 이 URL을 ConsultingAgent의 citations에 사용하세요:")
        print(f'   url: "{public_url}"')
        
        # URL을 파일로 저장
        url_file = os.path.join(os.path.dirname(__file__), "docs", "score_doc_url.txt")
        with open(url_file, 'w') as f:
            f.write(public_url)
        print(f"\n✅ URL 저장: {url_file}")
        
        return public_url
    else:
        print(f"\n❌ 업로드 실패")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("표준점수 산출 방식 문서 업로드")
    print("=" * 60)
    
    url = upload_score_calculation_pdf()
    
    if url:
        print(f"\n" + "=" * 60)
        print("✅ 업로드 성공!")
        print("=" * 60)
    else:
        print(f"\n" + "=" * 60)
        print("❌ 업로드 실패")
        print("=" * 60)
