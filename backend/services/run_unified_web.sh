#!/bin/bash

# UniZ 통합 웹 테스트 환경 실행 스크립트

echo "========================================"
echo "  UniZ 통합 웹 테스트 환경"
echo "========================================"
echo ""
echo "🌐 웹 브라우저에서 접속: http://localhost:8095"
echo ""
echo "상단 탭:"
echo "  1️⃣ Orchestration Agent"
echo "  2️⃣ Sub Agent"  
echo "  3️⃣ Final Pipeline"
echo ""
echo "========================================"
echo ""

cd /Users/rlaxogns100/Desktop/Projects/UniZ/backend/services
python3 test_unified_server.py
