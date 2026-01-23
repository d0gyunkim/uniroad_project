#!/bin/bash

# 구 테스트 파일 정리 스크립트

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  구 테스트 파일 정리${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}다음 파일들을 삭제합니다:${NC}"
echo ""

# 삭제할 파일 목록
FILES_TO_DELETE=(
    "test_admission_agent_simple.py"
    "test_agent_auto.py"
    "test_consulting_simple.py"
    "test_khu_integration.py"
    "test_khu_simple.py"
    "test_score_extraction.py"
    "test_university_scores.py"
)

# 파일 존재 확인 및 출력
FOUND_FILES=()
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${RED}✗${NC} $file"
        FOUND_FILES+=("$file")
    else
        echo -e "  ${YELLOW}?${NC} $file (존재하지 않음)"
    fi
done

echo ""
echo -e "${BLUE}유지되는 파일:${NC}"
echo -e "  ${GREEN}✓${NC} test_unified.py (통합 테스트 환경)"
echo -e "  ${GREEN}✓${NC} test_consulting_agent.py (상세 테스트용)"
echo -e "  ${GREEN}✓${NC} test_all_universities.py (5개 대학 테스트)"
echo -e "  ${GREEN}✓${NC} test_final_integration.py (통합 테스트)"
echo -e "  ${GREEN}✓${NC} test_full_pipeline.py (파이프라인 테스트)"
echo -e "  ${GREEN}✓${NC} test_raw_score.py (원점수 변환 - 선택적)"

echo ""
echo -e "${YELLOW}정말로 ${#FOUND_FILES[@]}개의 파일을 삭제하시겠습니까?${NC}"
echo -e "${YELLOW}(y/N):${NC} "
read -r CONFIRM

if [[ $CONFIRM =~ ^[Yy]$ ]]; then
    echo ""
    for file in "${FOUND_FILES[@]}"; do
        rm "$file"
        echo -e "${GREEN}✓${NC} 삭제됨: $file"
    done
    echo ""
    echo -e "${GREEN}✅ ${#FOUND_FILES[@]}개의 파일이 삭제되었습니다${NC}"
else
    echo ""
    echo -e "${BLUE}ℹ️  삭제가 취소되었습니다${NC}"
fi

echo ""
echo -e "${BLUE}======================================${NC}"
