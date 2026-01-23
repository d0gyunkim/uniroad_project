# Quick Start Guide - Agent Test Environments

새로 추가된 Orchestration Agent Test와 Sub Agent Test 환경 빠른 시작 가이드

## 🚀 빠른 실행

### 1️⃣ Orchestration Agent Test (포트 8091)

```bash
# 1. 디렉토리 이동
cd agent-tests/orchestration-agent-test/backend

# 2. 의존성 설치 (최초 1회)
pip install -r ../requirements.txt

# 3. 서버 실행
python main.py

# 4. 브라우저에서 ../index.html 열기
```

**테스트 예시**:
1. Agent 선택 안함 → 질문 입력: "나 11232야. 서울대 갈 수 있어?"
2. 실행 버튼 클릭
3. 결과 확인:
   - User Intent: 사용자 의도 분석
   - Execution Plan: 호출할 Agent 순서
   - Answer Structure: 답변 구조 설계

---

### 2️⃣ Sub Agent Test (포트 8092)

```bash
# 1. 디렉토리 이동
cd agent-tests/sub-agent-test/backend

# 2. 의존성 설치 (최초 1회)
pip install -r ../requirements.txt

# 3. 서버 실행
python main.py

# 4. 브라우저에서 ../index.html 열기
```

**테스트 예시**:

#### UniversityAgent (대학 정보 검색)
1. Agent 타입: `university`
2. 대학 선택: `서울대`
3. 쿼리: `2025학년도 정시 의예과 모집 인원`
4. 실행 → Supabase에서 실제 문서 검색

#### ConsultingAgent (성적 분석)
1. Agent 타입: `consulting`
2. 쿼리: `나 11232야. 경희대 의대 갈 수 있어?`
3. 실행 → 정규화된 성적 및 환산 점수 확인

#### TeacherAgent (학습 조언)
1. Agent 타입: `teacher`
2. 쿼리: `내신 2등급인데 수시로 어디까지 쓸 수 있을까요?`
3. 실행 → 학습 계획 및 조언 확인

---

## 🎯 프롬프트 수정 워크플로우

### Orchestration Agent 프롬프트 수정

1. **기본 프롬프트 불러오기**
   - "📄 기본 프롬프트 불러오기" 버튼 클릭
   - 커스텀 프롬프트 영역에 프롬프트 표시됨

2. **프롬프트 수정**
   - 원하는 부분 수정 (예: 간결성 원칙 강화)
   - **주의**: `{agents}` 플레이스홀더는 반드시 유지

3. **테스트**
   - 질문 입력 후 실행
   - 결과 확인

4. **저장**
   - "💾 프롬프트 저장" 버튼 클릭
   - 이름 및 설명 입력 후 저장

5. **재사용**
   - "📂 프롬프트 불러오기" 버튼으로 저장된 프롬프트 불러오기

---

### Sub Agent 프롬프트 수정 (ConsultingAgent / TeacherAgent)

1. **Agent 타입 선택**
   - `consulting` 또는 `teacher` 선택

2. **기본 프롬프트 불러오기**
   - "📄 기본 프롬프트 불러오기" 버튼 클릭

3. **프롬프트 수정**
   - ConsultingAgent: 출력 형식, 톤앤매너 조정
   - TeacherAgent: 조언 원칙, 멘토 페르소나 조정

4. **테스트 & 저장**
   - 동일한 워크플로우

---

## 📊 데이터셋 활용

### 데이터셋 저장
- 자주 사용하는 질문을 데이터셋으로 저장
- Agent 타입별로 관리

### 데이터셋 불러오기
- 저장된 질문 즉시 불러오기
- 반복 테스트에 활용

---

## 🔍 주요 차이점

| 항목 | Orchestration Agent Test | Sub Agent Test | Final Agent Test |
|------|-------------------------|----------------|------------------|
| **목적** | 실행 계획 수립 | 실제 데이터 검색/분석 | 최종 답변 생성 |
| **입력** | 사용자 질문 | Agent별 쿼리 | 구조화된 데이터 |
| **출력** | Execution Plan + Answer Structure | Agent 결과 (검색/분석) | 최종 답변 텍스트 |
| **DB 연결** | ❌ | ✅ (UniversityAgent) | ❌ |
| **점수 계산** | ❌ | ✅ (ConsultingAgent) | ❌ |
| **프롬프트 수정** | ✅ | ✅ (일부) | ✅ |

---

## 🛠️ 트러블슈팅

### API 키 오류
```
[WARNING] No API key found
```
→ 프로젝트 루트의 `.env` 파일에 `GEMINI_API_KEY` 설정 확인

### Supabase 연결 오류 (Sub Agent Test)
```
Supabase connection failed
```
→ `.env` 파일에 `SUPABASE_URL`, `SUPABASE_KEY` 설정 확인

### 포트 충돌
```
Address already in use
```
→ 다른 테스트 환경이 이미 실행 중인지 확인
→ `lsof -i :8091` 또는 `lsof -i :8092`로 확인

### 모듈 import 오류
```
ModuleNotFoundError: No module named 'services'
```
→ 메인 프로젝트의 backend 디렉토리가 Python path에 추가되었는지 확인
→ `sys.path.insert(0, str(backend_path))` 부분 확인

---

## 📝 다음 단계

1. **프롬프트 최적화**
   - 각 Agent별로 프롬프트 수정 및 테스트
   - 최적화된 프롬프트 저장

2. **데이터셋 구축**
   - 다양한 질문 패턴 저장
   - Edge case 테스트

3. **프로덕션 적용**
   - 최적화된 프롬프트를 메인 프로젝트에 적용
   - `backend/services/multi_agent/` 업데이트

---

## 💡 팁

- **Orchestration Agent**: 간결성 원칙을 조정하여 Agent 호출 최소화
- **ConsultingAgent**: 출력 형식을 조정하여 가독성 향상
- **TeacherAgent**: 톤앤매너를 조정하여 학생 공감도 향상
- **데이터셋**: 성공/실패 케이스를 모두 저장하여 회귀 테스트에 활용
