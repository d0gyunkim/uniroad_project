#!/bin/bash

echo "🛑 유니로드 서버 종료 중..."
echo "=================================="
echo ""

# 백엔드 프로세스 종료
BACKEND_PIDS=$(pgrep -f "python.*main.py")
if [ -n "$BACKEND_PIDS" ]; then
    echo "🔧 백엔드 서버 종료 중..."
    pkill -f "python.*main.py"
    echo "   ✅ 백엔드 서버 종료 완료"
else
    echo "   ℹ️  실행 중인 백엔드 서버 없음"
fi

# 프론트엔드 프로세스 종료
FRONTEND_PIDS=$(pgrep -f "vite")
if [ -n "$FRONTEND_PIDS" ]; then
    echo "⚡ 프론트엔드 서버 종료 중..."
    pkill -f "vite"
    echo "   ✅ 프론트엔드 서버 종료 완료"
else
    echo "   ℹ️  실행 중인 프론트엔드 서버 없음"
fi

echo ""
echo "✅ 모든 서버가 종료되었습니다"
echo "=================================="
