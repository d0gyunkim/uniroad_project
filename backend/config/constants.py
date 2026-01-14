"""
상수 정의
"""

# 파일 업로드 설정
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# 텍스트 청킹 설정
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# 임베딩 설정
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768  # Gemini 임베딩 차원
BATCH_SIZE = 5  # Gemini 병렬 처리 개수

# RAG 검색 설정
TOP_CHUNKS_COUNT = 3
KEYWORD_DENSITY_WEIGHT = 0.5
VECTOR_MATCH_THRESHOLD = 0.78

# 요약 설정
SUMMARY_MAX_LENGTH = 500
CLASSIFICATION_SAMPLE_LENGTH = 2000

# 문서 분류 설정
IMPORTANT_KEYWORDS = [
    '2028', '2029', '2030',
    '입학', '전형', '개편',
    '서울대', '면접', '평가',
    '수시', '정시', '학생부'
]

# API 타임아웃 설정
API_TIMEOUT_SECONDS = 120

# Gemini 모델
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"  # 대화/판단용 (고품질)
GEMINI_LITE_MODEL = "gemini-2.5-flash-lite"    # 문서 처리용 (고속)
