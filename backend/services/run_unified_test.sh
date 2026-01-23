#!/bin/bash

# UniZ 통합 테스트 환경 실행 스크립트

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  UniZ 통합 테스트 환경 시작${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}✅ 작업 디렉토리: $SCRIPT_DIR${NC}"

# .env 파일 확인
if [ -f "../.env" ]; then
    echo -e "${GREEN}✅ .env 파일 발견${NC}"
else
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다${NC}"
    echo -e "${YELLOW}   Final Integration 테스트는 GEMINI_API_KEY가 필요합니다${NC}"
fi

# Python 버전 확인
echo -e "${BLUE}ℹ️  Python 버전:${NC}"
python3 --version

echo ""
echo -e "${BLUE}테스트 환경을 실행합니다...${NC}"
echo ""

# 통합 테스트 실행
python3 test_unified.py

# 종료 코드 확인
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 테스트가 정상적으로 종료되었습니다${NC}"
else
    echo ""
    echo -e "${RED}❌ 테스트 실행 중 오류가 발생했습니다 (Exit Code: $EXIT_CODE)${NC}"
    echo ""
    echo -e "${YELLOW}문제 해결:${NC}"
    echo -e "  1. Python 패키지 업데이트: ${BLUE}pip install --upgrade pydantic supabase${NC}"
    echo -e "  2. .env 파일 확인: ${BLUE}cat ../.env${NC}"
    echo -e "  3. 자세한 가이드: ${BLUE}cat TEST_README.md${NC}"
fi

exit $EXIT_CODE
