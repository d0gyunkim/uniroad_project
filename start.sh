#!/bin/bash

echo "🚀 유니로드 서버 시작"
echo "=================================="
echo ""

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# 기존 프로세스 종료
echo "🧹 기존 서버 프로세스 정리 중..."
pkill -f "python.*main.py" 2>/dev/null
pkill -f "vite" 2>/dev/null
sleep 1

# 터미널 창 2개로 실행
if command -v osascript &> /dev/null; then
    # macOS
    echo "📱 macOS 감지 - 터미널 2개 자동 실행"
    echo ""
    
    # 백엔드 터미널 (venv 없이 실행)
    osascript -e 'tell application "Terminal"
        do script "cd \"'"$PROJECT_ROOT"'/backend\" && echo \"🔧 백엔드 서버 시작 중...\" && python3 main.py; read -p \"서버가 종료되었습니다. 아무 키나 누르세요...\""
    end tell' > /dev/null 2>&1
    
    sleep 2
    
    # 프론트엔드 터미널
    osascript -e 'tell application "Terminal"
        do script "cd \"'"$PROJECT_ROOT"'/frontend\" && echo \"⚡ 프론트엔드 서버 시작 중...\" && npm run dev; read -p \"서버가 종료되었습니다. 아무 키나 누르세요...\""
    end tell' > /dev/null 2>&1
    
    sleep 3
    
    echo "✅ 서버 시작 완료!"
    echo ""
    echo "📍 접속 주소:"
    echo "   프론트엔드: http://localhost:5173"
    echo "   백엔드 API: http://localhost:8000"
    echo "   API 문서: http://localhost:8000/docs"
    echo "   관리자 페이지: http://localhost:5173/admin/agent"
    echo ""
    echo "⚠️  서버 종료 방법:"
    echo "   각 터미널 창에서 Ctrl+C를 누르세요"
    echo ""
    echo "🔍 서버 상태 확인:"
    sleep 2
    
    # 백엔드 확인
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "   ✅ 백엔드: 정상 실행 중"
    else
        echo "   ⏳ 백엔드: 시작 중... (3초 후 재확인)"
        sleep 3
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo "   ✅ 백엔드: 정상 실행 중"
        else
            echo "   ❌ 백엔드: 실행 실패 (터미널 창 확인)"
        fi
    fi
    
    # 프론트엔드 확인
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "   ✅ 프론트엔드: 정상 실행 중"
    else
        echo "   ⏳ 프론트엔드: 시작 중..."
    fi
    
else
    # Linux/기타
    echo "⚠️  수동으로 2개 터미널에서 실행하세요:"
    echo ""
    echo "터미널 1 (백엔드):"
    echo "  cd $PROJECT_ROOT/backend"
    echo "  python3 main.py"
    echo ""
    echo "터미널 2 (프론트엔드):"
    echo "  cd $PROJECT_ROOT/frontend"
    echo "  npm run dev"
fi

echo ""
echo "=================================="

