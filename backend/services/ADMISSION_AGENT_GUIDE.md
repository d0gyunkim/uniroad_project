# 대학 입시 데이터 분석 에이전트 사용 가이드

## 개요

2026 수능 데이터를 기반으로 사용자의 성적을 분석하는 AI 에이전트입니다.
- **모델**: Gemini 2.0 Flash Preview
- **기능**: 점수 변환, 등급 추정, 성적 분석

## 설치 및 설정

### 1. 필수 패키지 설치

```bash
pip install google-generativeai
```

### 2. Gemini API 키 설정

#### 방법 1: 환경변수로 설정 (권장)

**macOS/Linux:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

**영구 설정 (macOS/Linux - ~/.zshrc 또는 ~/.bashrc):**
```bash
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

#### 방법 2: 실행 시 직접 입력
프로그램 실행 시 API 키 입력 프롬프트가 표시됩니다.

### 3. Gemini API 키 발급 방법

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Create API Key" 클릭
3. 생성된 키 복사

## 실행 방법

### 기본 실행

```bash
cd backend/services
python3 admission_agent.py
```

### 환경변수와 함께 실행

```bash
GEMINI_API_KEY="your-api-key" python3 admission_agent.py
```

## 사용 예시

### 예시 1: 등급으로 입력
```
📝 입력: 등급 132

→ 국어 1등급, 영어 3등급, 수학 2등급으로 해석하여 분석
```

### 예시 2: 원점수로 입력
```
📝 입력: 국어 언어와매체 92점, 수학 미적분 77점

→ 선택과목을 고려한 표준점수/백분위 변환 및 분석
```

### 예시 3: 혼합 입력
```
📝 입력: 국어 1등급 수학 백분위 95 영어 2등급

→ 다양한 형식의 입력을 통합하여 분석
```

### 예시 4: 간단한 입력
```
📝 입력: 국어 90 수학 85

→ 선택과목을 추론하고(화법과작문/확률과통계) 분석
→ 미입력 과목(영어, 탐구)은 유사한 백분위로 추정
```

## 에이전트 기능

### 1. 입력 해석 및 정규화
- 모호한 입력을 2026 수능 데이터 기준으로 표준화
- 선택과목 자동 추론 (국어/수학)
- 미입력 과목 추정

### 2. 점수 변환
- 등급 → 표준점수/백분위
- 원점수 → 표준점수/백분위
- 백분위 → 표준점수/등급
- 선형 보간을 통한 정밀한 점수 추정

### 3. 성적 분석
- 전반적인 성적 수준 평가
- 강점 과목 파악
- 개선이 필요한 과목 제안

## 지원 과목

### 국어
- 선택과목: 화법과작문, 언어와매체

### 수학
- 선택과목: 확률과통계, 미적분, 기하

### 영어
- 절대평가 (등급만 제공)

### 사회탐구 (9과목)
경제, 동아시아사, 사회문화, 생활과윤리, 세계사, 세계지리, 정치와법, 한국지리, 윤리와사상

### 과학탐구 (8과목)
물리학1, 물리학2, 화학1, 화학2, 생명과학1, 생명과학2, 지구과학1, 지구과학2

## 종료

터미널에서 다음 중 하나를 입력:
- `exit`
- `quit`
- `q`
- `Ctrl+C`

## 트러블슈팅

### 1. "GEMINI_API_KEY가 설정되지 않았습니다" 오류
**해결방법**: API 키를 환경변수로 설정하거나 실행 시 직접 입력

### 2. "google-generativeai 패키지가 설치되어 있지 않습니다" 오류
**해결방법**: 
```bash
pip3 install google-generativeai
```

### 3. 네트워크 오류
**해결방법**: 
- 인터넷 연결 확인
- API 키가 유효한지 확인
- Google AI Studio에서 API 키 상태 확인

### 4. 모델 응답 오류
**해결방법**: 
- Gemini API 쿼터 확인
- 입력이 너무 길지 않은지 확인
- API 키가 만료되지 않았는지 확인

## 프로그래밍 방식 사용

```python
from admission_agent import AdmissionAgent

# 에이전트 초기화
agent = AdmissionAgent(api_key="your-api-key")

# 메시지 전송
response = agent.send_message("등급 132")
print(response)

# ScoreConverter 직접 사용
result = agent.convert_score("국어", raw_score=92, elective="언어와매체")
print(result)
```

## 주의사항

1. API 키는 절대 공개 저장소에 커밋하지 마세요
2. Gemini API는 사용량 제한이 있을 수 있습니다
3. 네트워크 연결이 필요합니다
4. 추정된 점수는 실제와 다를 수 있습니다

## 라이선스

교육 목적으로 제공됩니다.
