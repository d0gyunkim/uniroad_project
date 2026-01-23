# 🌐 UniZ 통합 웹 테스트 환경

## 완성! ✅

3개의 테스트 환경을 **하나의 웹 UI**로 통합했습니다!

## 🚀 실행 방법

### 방법 1: 빠른 실행
```bash
cd /Users/rlaxogns100/Desktop/Projects/UniZ/backend/services
./run_unified_web.sh
```

### 방법 2: 직접 실행
```bash
cd /Users/rlaxogns100/Desktop/Projects/UniZ/backend/services
python3 test_unified_server.py
```

## 🌐 접속

서버가 실행되면 웹 브라우저를 열고:

```
http://localhost:8095
```

## 📱 화면 구성

### 상단 탭 (클릭해서 전환)
- **🎯 Orchestration Agent** - 질문 분석 & 실행 계획 수립
- **📊 Sub Agent** - 개별 Agent 테스트 (대학별/컨설팅/선생님)
- **🚀 Final Pipeline** - 전체 파이프라인 (Gemini API 포함)

### 좌우 분할
- **왼쪽**: 입력 패널 (질문 입력, 설정 등)
- **오른쪽**: 출력 패널 (실행 결과)

## 📝 사용 예시

### 1️⃣ Orchestration Agent 테스트
```
입력: 나 11232야
결과: 
- 사용자 의도 분석
- 실행 계획 (Execution Plan)
- 답변 구조 (Answer Structure)
```

### 2️⃣ Sub Agent 테스트
```
Agent: 컨설팅 Agent
입력: 나 13425야. 경희대 의대 갈 수 있어?
결과:
- 성적 정규화
- 대학별 환산 점수
- 합격 가능성 분석
```

### 3️⃣ Final Pipeline 테스트
```
입력: 나 11111이야. SKY랑 서강대, 경희대 중에서 어디가 유리해?
결과:
- Orchestration 결과
- Sub Agent 실행 결과
- 최종 답변 (Gemini 생성)
```

## 🎨 디자인

기존 테스트 환경의 디자인을 그대로 유지했습니다:
- **다크 테마** (왼쪽 입력 패널)
- **라이트 테마** (오른쪽 출력 패널)
- **깔끔한 분할 레이아웃**
- **상단 탭 네비게이션**

## 🔧 기술 스택

- **Frontend**: HTML + CSS + Vanilla JavaScript
- **Backend**: FastAPI (Python)
- **API**: 
  - `/api/orchestration` - Orchestration Agent
  - `/api/subagent` - Sub Agent
  - `/api/chat` - Full Pipeline

## 📁 파일 구조

```
backend/services/
├── test_unified_web.html          # 프론트엔드 (통합 UI)
├── test_unified_server.py         # 백엔드 서버 (FastAPI)
├── run_unified_web.sh             # 실행 스크립트
└── WEB_TEST_README.md             # 이 파일
```

## 🗑️ 기존 테스트 환경과의 차이

### 기존 (agent-tests/)
- 3개의 독립적인 웹 환경
- 각각 별도의 HTML + 서버
- 매번 다른 포트로 접속

### 새로운 통합 환경
- ✅ **하나의 웹 페이지**
- ✅ **상단 탭으로 전환**
- ✅ **하나의 포트 (8095)**
- ✅ **통일된 디자인**

## 🎯 장점

1. **빠른 전환**: 탭 클릭 한 번으로 테스트 전환
2. **통일된 UI**: 일관된 디자인으로 사용성 향상
3. **간편한 실행**: 하나의 서버만 실행하면 됨
4. **효율적인 개발**: 코드 중복 제거

## 📞 문제 해결

### 서버가 시작되지 않음
```bash
# 기존 프로세스 종료
lsof -ti:8095 | xargs kill -9

# 다시 실행
./run_unified_web.sh
```

### 웹 페이지가 안 열림
```bash
# 서버 상태 확인
curl http://localhost:8095/health

# 결과: {"status":"ok","message":"UniZ 통합 테스트 서버 정상 작동 중"}
```

### API 호출 실패
- `.env` 파일에 `GEMINI_API_KEY` 확인
- Backend 로그 확인

## 🎉 완성!

이제 **하나의 웹 페이지**에서 모든 테스트를 할 수 있습니다!

웹 브라우저를 열고 http://localhost:8095 에 접속하세요! 🚀
