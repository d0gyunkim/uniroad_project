# 🎓 유니로드 (UniZ)

대학 입시 상담 AI 플랫폼 - 멀티에이전트 기반 입시 컨설팅 서비스

## 🚀 빠른 시작

### 1. 서버 시작 (한 번에!)
```bash
./start.sh
```

### 2. 서버 종료
```bash
./stop.sh
```

### 3. 접속 주소
- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **관리자 페이지**: http://localhost:5173/admin/agent

---

## 📦 수동 설치 및 실행

### 환경 요구사항
- Python 3.9+
- Node.js 18+
- npm 9+

### 백엔드 설정
```bash
cd backend

# 환경 변수 설정 (.env 파일 생성)
# SUPABASE_URL=your-url
# SUPABASE_KEY=your-key
# GEMINI_API_KEY=your-key

# 의존성 설치
pip3 install -r requirements.txt

# 서버 실행
python3 main.py
```

### 프론트엔드 설정
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

---

## 🏗️ 프로젝트 구조

```
UniZ/
├── backend/               # FastAPI 백엔드
│   ├── main.py           # 메인 애플리케이션
│   ├── routers/          # API 라우터
│   │   ├── chat.py       # 채팅 API
│   │   ├── agent_admin.py # 에이전트 관리
│   │   └── ...
│   ├── services/         # 비즈니스 로직
│   │   ├── multi_agent/  # 멀티에이전트 시스템
│   │   │   ├── orchestration_agent.py  # 오케스트레이션
│   │   │   ├── sub_agents.py           # Sub Agents
│   │   │   └── final_agent.py          # Final Agent
│   │   ├── khu_score_calculator.py     # 경희대 환산 점수
│   │   ├── snu_score_calculator.py     # 서울대 환산 점수
│   │   ├── yonsei_score_calculator.py  # 연세대 환산 점수
│   │   ├── korea_score_calculator.py   # 고려대 환산 점수
│   │   └── sogang_score_calculator.py  # 서강대 환산 점수
│   └── ...
├── frontend/             # React + TypeScript 프론트엔드
│   ├── src/
│   │   ├── pages/        # 페이지 컴포넌트
│   │   │   ├── ChatPage.tsx        # 채팅 페이지
│   │   │   └── AgentAdminPage.tsx  # 관리자 페이지
│   │   └── components/   # 재사용 컴포넌트
│   └── ...
├── start.sh              # 서버 시작 스크립트
├── stop.sh               # 서버 종료 스크립트
└── README.md
```

---

## 🤖 멀티에이전트 시스템

### 아키텍처
```
User Query
    ↓
Orchestration Agent (질문 분석 + 실행 계획)
    ↓
Sub Agents (병렬 실행)
    ├─ University Agents (서울대/연세대/고려대/성균관대/경희대)
    ├─ Consulting Agent (입결 분석 + 환산 점수 계산)
    └─ Teacher Agent (학습 계획 + 멘탈 관리)
    ↓
Final Agent (최종 답변 생성)
    ↓
User Answer
```

### 주요 기능
1. **대학별 환산 점수 자동 계산** (5개 대학)
   - 경희대 (600점 만점)
   - 서울대 (1000점 스케일)
   - 연세대 (1000점 만점)
   - 고려대 (1000점 환산)
   - 서강대 (A/B형 최고점)

2. **입시 정보 검색**
   - Supabase 기반 RAG 시스템
   - 해시태그 기반 문서 필터링
   - 출처 자동 표시

3. **관리자 페이지**
   - 에이전트 플로우 시각화
   - 프롬프트 버전 관리
   - 실시간 로그 모니터링

---

## 🔧 문제 해결

### 서버가 시작되지 않을 때
```bash
# 1. 기존 프로세스 종료
./stop.sh

# 2. 포트 사용 확인
lsof -i :8000  # 백엔드
lsof -i :5173  # 프론트엔드

# 3. 서버 재시작
./start.sh
```

### 프론트엔드 의존성 오류
```bash
cd frontend
npm install
```

### 백엔드 API 연결 실패
```bash
# 백엔드 health check
curl http://localhost:8000/api/health

# 응답이 없으면 백엔드 재시작
cd backend
python3 main.py
```

---

## 📝 개발 가이드

### 새로운 대학 환산 점수 추가
1. `backend/services/{university}_score_calculator.py` 생성
2. `calculate_{university}_score()` 함수 구현
3. `sub_agents.py`의 `ConsultingAgent.execute()`에 통합
4. 포맷팅 메서드 추가 (`_format_{university}_scores`)

### 새로운 Sub Agent 추가
1. `sub_agents.py`에 클래스 정의
2. `execute()` 메서드 구현
3. `orchestration_agent.py`의 `AVAILABLE_AGENTS`에 등록
4. `agent_admin.py`의 `AGENT_DEFINITIONS`에 추가

---

## 📊 성능 모니터링

### 토큰 사용량 확인
```bash
cd backend
python3 view_token_stats.py
```

### 로그 확인
- 백엔드: 터미널 출력
- 프론트엔드: 브라우저 콘솔
- Agent 실행: 관리자 페이지 로그 패널

---

## 🔒 보안

### 환경 변수 (.env)
```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
GEMINI_API_KEY=your-gemini-api-key
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

⚠️ **주의**: `.env` 파일은 절대 Git에 커밋하지 마세요!

---

## 📄 라이센스

MIT License

---

## 👥 팀

개발: 유니로드 팀

---

## 🆘 지원

문제가 발생하면:
1. `./stop.sh` 실행
2. `./start.sh` 실행
3. 여전히 문제가 있으면 각 터미널의 에러 로그 확인

**Happy Coding! 🚀**
