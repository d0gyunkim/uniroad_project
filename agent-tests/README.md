# Agent Tests

UniZ 프로젝트의 에이전트 테스트 환경 모음입니다.

## 구조

```
agent-tests/
├── README.md                           # 이 파일
├── orchestration-agent-test/           # Orchestration Agent 단독 테스트 (NEW!)
│   ├── backend/
│   │   ├── main.py
│   │   └── storage/
│   ├── index.html
│   ├── requirements.txt
│   └── README.md
├── sub-agent-test/                     # Sub Agent 단독 테스트 (NEW!)
│   ├── backend/
│   │   ├── main.py
│   │   └── storage/
│   ├── index.html
│   ├── requirements.txt
│   └── README.md
├── final-agent-test/                   # Final Agent 단독 테스트
│   ├── backend/
│   │   ├── main.py
│   │   └── storage/
│   ├── index.html
│   ├── requirements.txt
│   └── README.md
└── orchestration-test/                 # 전체 파이프라인 테스트 (레거시)
    ├── backend/
    │   ├── main.py
    │   ├── final_agent.py
    │   ├── sub_agents.py
    │   └── mock_database.py
    ├── frontend/
    │   └── index.html
    ├── requirements.txt
    └── README.md
```

## 🎯 새로운 테스트 환경 (프로덕션 동일 구현)

### 1️⃣ Orchestration Agent Test (포트: 8091)

**목적**: Orchestration Agent만 단독으로 테스트

**특징**:
- ✅ 프로덕션과 100% 동일한 시스템 프롬프트
- ✅ 커스텀 프롬프트 지원
- ✅ 프롬프트/데이터셋 저장/불러오기
- ✅ Execution Plan & Answer Structure 확인
- ✅ 즉시 응답 (Direct Response) 지원

**실행**:
```bash
cd orchestration-agent-test/backend
python main.py
# 브라우저에서 index.html 열기
```

**테스트 예시**:
- "나 11232야. 서울대 갈 수 있어?" → Execution Plan 생성 확인
- "안녕" → 즉시 응답 (Direct Response) 확인

---

### 2️⃣ Sub Agent Test (포트: 8092)

**목적**: Sub Agent들을 개별적으로 테스트 (실제 DB 연결)

**특징**:
- ✅ 프로덕션과 100% 동일한 로직
- ✅ **실제 Supabase DB 연결** (UniversityAgent)
- ✅ **실제 Python 함수 연결** (점수 계산기들)
- ✅ 3가지 Agent 타입 지원:
  - 🏫 UniversityAgent (대학별 정보 검색)
  - 📊 ConsultingAgent (성적 분석 및 환산)
  - 👨‍🏫 TeacherAgent (학습 계획 및 조언)
- ✅ ConsultingAgent/TeacherAgent 커스텀 프롬프트 지원
- ✅ 프롬프트/데이터셋 저장/불러오기
- ✅ 정규화된 성적 및 환산 점수 확인

**실행**:
```bash
cd sub-agent-test/backend
python main.py
# 브라우저에서 index.html 열기
```

**테스트 예시**:
- UniversityAgent: "서울대 2025학년도 정시 의예과 모집 인원"
- ConsultingAgent: "나 11232야. 경희대 의대 갈 수 있어?"
- TeacherAgent: "내신 2등급인데 수시로 어디까지 쓸 수 있을까요?"

---

### 3️⃣ Final Agent Test (포트: 8090)

**목적**: Final Agent만 단독 테스트 (기존)

**특징**:
- ✅ 프로덕션과 100% 동일한 프롬프트
- ✅ 직접 입력으로 프롬프트 최적화
- ✅ 커스텀 프롬프트 지원
- ✅ 프롬프트/데이터셋 저장/불러오기

**실행**:
```bash
cd final-agent-test/backend
python main.py
# 브라우저에서 index.html 열기
```

---

## 🔄 레거시 테스트 환경

### 4️⃣ Orchestration Test (포트: 8080)

전체 Multi-Agent 파이프라인 테스트 (레거시):
- Orchestration Agent → Sub Agents → Final Agent

```bash
cd orchestration-test/backend
python main.py
```

---

## 환경 설정

`.env` 파일이 프로젝트 루트에 있어야 합니다:

```
GEMINI_API_KEY=your-api-key-here
SUPABASE_URL=your-supabase-url          # Sub Agent Test에서 필요
SUPABASE_KEY=your-supabase-key          # Sub Agent Test에서 필요
```

## 포트 정보

| 테스트 환경 | 포트 | 프론트엔드 | 비고 |
|------------|------|-----------|------|
| **Orchestration Agent Test** | **8091** | index.html | NEW! 단독 테스트 |
| **Sub Agent Test** | **8092** | index.html | NEW! 실제 DB 연결 |
| Final Agent Test | 8090 | index.html | 기존 |
| Orchestration Test (레거시) | 8080 | frontend/index.html | 전체 파이프라인 |

## 사용 권장 사항

### 프롬프트 최적화 워크플로우

1. **Orchestration Agent 프롬프트 수정** → `orchestration-agent-test` 사용
2. **Sub Agent 프롬프트 수정** → `sub-agent-test` 사용
3. **Final Agent 프롬프트 수정** → `final-agent-test` 사용
4. **전체 파이프라인 테스트** → `orchestration-test` 사용

### 각 Agent별 테스트 우선순위

- **Orchestration Agent**: Execution Plan과 Answer Structure 설계 검증
- **Sub Agent**: 실제 데이터 검색 및 점수 계산 로직 검증
- **Final Agent**: 최종 답변 생성 및 포맷팅 검증
