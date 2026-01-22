"""
Supabase에서 사용자 목록 조회 스크립트
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# .env 파일 로드
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
    exit(1)

# Supabase 클라이언트 생성
client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("\n" + "="*60)
print("현재 계정 목록 (chat_sessions 테이블 기반)")
print("="*60)

try:
    # chat_sessions 테이블에서 user_id 조회
    response = client.table('chat_sessions').select('user_id, created_at').execute()
    
    if not response.data:
        print("❌ 세션 데이터가 없습니다.")
    else:
        # user_id별로 그룹화
        user_ids = {}
        for row in response.data:
            user_id = row['user_id']
            if user_id not in user_ids:
                user_ids[user_id] = row['created_at']
        
        print(f"\n총 {len(user_ids)}명의 사용자:")
        for idx, (user_id, created_at) in enumerate(user_ids.items(), 1):
            print(f"{idx}. User ID: {user_id}")
            print(f"   가입일: {created_at}")
            print()
    
    # chat_messages 테이블에서도 확인
    print("\n" + "="*60)
    print("메시지 테이블 기반 사용자 목록")
    print("="*60)
    
    response2 = client.table('chat_messages').select('user_id').execute()
    
    if response2.data:
        user_ids_from_messages = set(row['user_id'] for row in response2.data if row.get('user_id'))
        print(f"\n메시지를 보낸 사용자 수: {len(user_ids_from_messages)}")
        for idx, user_id in enumerate(sorted(user_ids_from_messages), 1):
            print(f"{idx}. User ID: {user_id}")
    
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("참고: Supabase Auth의 전체 사용자 정보를 보려면")
print("Supabase Dashboard > Authentication > Users에서 확인하세요.")
print("="*60 + "\n")
