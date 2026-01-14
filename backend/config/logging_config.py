"""
로깅 설정
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

# 로그 디렉토리 생성
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 로그 파일 이름 (날짜별)
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"


def setup_logger(name: str) -> logging.Logger:
    """
    로거 설정

    Args:
        name: 로거 이름 (보통 모듈 이름)

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 있으면 반환 (중복 방지)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 파일 핸들러
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 전역 로거들
api_logger = setup_logger('api')
rag_logger = setup_logger('rag')
upload_logger = setup_logger('upload')
classifier_logger = setup_logger('classifier')
embedding_logger = setup_logger('embedding')
