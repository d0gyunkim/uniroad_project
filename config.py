"""
설정 파일
환경 변수 및 기본 설정값 관리
"""
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv(override=True)

# API Key 설정
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    os.environ["GOOGLE_API_KEY"] = gemini_key

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
if UPSTAGE_API_KEY:
    os.environ["UPSTAGE_API_KEY"] = UPSTAGE_API_KEY

# 기본 모델 설정
# 참고: gemini-3.0-flash-lite는 아직 사용 불가능합니다.
# 사용 가능한 모델: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp
DEFAULT_LLM_MODEL = "gemini-3-flash-preview"  # 빠르고 안정적인 최신 모델
DEFAULT_EMBEDDING_MODEL = "models/embedding-001"

# [변경 후] Long Context 전략 설정
# 청킹 설정
CHUNK_SIZE_TOKENS = 800       # 청크를 더 크게 잡아서 문맥이 안 잘리게 함 (표 데이터 보호)
CHUNK_OVERLAP_TOKENS = 150    # 오버랩도 넉넉하게

# 청킹 방식 설정
CHUNK_BY_PAGE = True          # True: 페이지 단위 청킹, False: 토큰 기반 청킹

# 검색 설정 (벡터 검색만 사용)
# VECTOR_SEARCH_WEIGHT = 0.7  # 사용하지 않음 (키워드 검색 제거)
# KEYWORD_SEARCH_WEIGHT = 0.3  # 사용하지 않음 (키워드 검색 제거)
TOP_K_PER_SECTION = 30        # 각 섹션에서 더 많이 긁어옴
TOP_K_FINAL = 10              # 최종적으로 LLM에게 50개 청크(약 3~4만 토큰)를 통째로 던짐

# 재시도 설정
DEFAULT_MAX_RETRIES = 3

# 병렬 처리 설정
MAX_WORKERS = 4  # 섹션 전처리 병렬 처리 최대 개수

# 캐시 디렉토리
CACHE_DIR = ".cache"
FILES_DIR = ".cache/files"
EMBEDDINGS_DIR = ".cache/embeddings"
TOC_SECTIONS_DIR = ".cache/toc_sections"

# 캐시 디렉토리 생성
for dir_path in [CACHE_DIR, FILES_DIR, EMBEDDINGS_DIR, TOC_SECTIONS_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

