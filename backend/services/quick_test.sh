#!/bin/bash
# 대학 입시 데이터 분석 에이전트 빠른 테스트 스크립트

echo "=========================================="
echo "🎓 대학 입시 데이터 분석 에이전트"
echo "=========================================="
echo ""

# API 키 확인
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY 환경변수가 설정되지 않았습니다."
    echo ""
    echo "API 키 설정 방법:"
    echo "  export GEMINI_API_KEY='your-api-key-here'"
    echo ""
    echo "또는 프로그램 실행 시 직접 입력할 수 있습니다."
    echo ""
else
    echo "✅ GEMINI_API_KEY 설정됨"
    echo ""
fi

# Python 버전 확인
echo "Python 버전:"
python3 --version
echo ""

# 필수 패키지 확인
echo "필수 패키지 확인:"
python3 -c "import google.generativeai; print('✅ google-generativeai installed')" 2>/dev/null || echo "❌ google-generativeai not installed"
echo ""

# 실행
echo "=========================================="
echo "에이전트 실행 중..."
echo "=========================================="
echo ""

cd "$(dirname "$0")"
python3 admission_agent.py
