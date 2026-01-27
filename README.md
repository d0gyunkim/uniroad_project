# 📑 목차 기반 동적 라우팅 RAG 시스템

Google Gemini를 활용한 **목차 기반 동적 라우팅 RAG (Retrieval-Augmented Generation)** 시스템입니다. 대학 입시 모집요강 PDF를 자동으로 분석하여 정확한 입시 정보를 제공합니다.

## 🎯 핵심 특징

- **📋 목차 자동 감지 및 파싱**: Gemini LLM으로 PDF 목차를 자동 인식하여 섹션별 구조화
- **🎯 동적 섹션 선택 및 Re-ranking**: 질문에 따라 관련 섹션만 선택하고 관련성 점수로 재순위화
- **👁️ Gemini Vision 기반 PDF 처리**: PDF 페이지를 이미지로 변환하여 Gemini Vision으로 마크다운 변환
  - 복잡한 레이아웃 정확히 인식
  - 표와 텍스트를 완벽하게 구조화
- **⚡ 다층 병렬 처리**: 섹션 전처리와 페이지 변환을 병렬로 수행하여 속도 극대화
- **📄 페이지 단위 청킹**: 각 페이지를 하나의 청크로 처리하여 정확한 페이지 번호 추적
- **📊 Dual Chunking 전략**: 표는 검색용 요약 + 원본 데이터로 분리 저장
  - 검색: 자연어 요약으로 의미 기반 검색
  - 답변: 원본 표 데이터로 상세 정보 제공
- **🔍 표/텍스트 분리 검색**: 표와 텍스트를 별도로 검색하여 정확도 향상
- **🤖 Gemini 표 분석**: 검색된 표를 Gemini로 분석하여 질문 관련 정보만 추출
- **✅ 품질 평가 및 재시도**: LLM 기반 답변 품질 평가 및 자동 재시도
- **💬 대화 연속성**: 이전 대화 맥락을 고려한 자연스러운 답변

## 🏗️ 시스템 아키텍처

### 전체 파이프라인 흐름

```
[초기화 단계]
PDF 업로드
  ↓
목차 감지 (처음 10페이지 스캔, Gemini LLM)
  ↓
목차 파싱 (Gemini LLM)
  ↓
섹션별 병렬 전처리 (최대 4개 섹션 동시)
  ├─ PDF 페이지 → 이미지 변환 (PyMuPDF, DPI 200)
  ├─ 페이지별 병렬 처리 (최대 4개 페이지 동시)
  │  └─ Gemini Vision → 마크다운 변환
  │     ├─ 표는 <table_summary> 태그로 요약 포함
  │     └─ 완벽한 Markdown 구조 보존
  ├─ Dual Chunking 처리
  │  ├─ 표: summary(검색용) + raw_data(원본) 분리
  │  └─ 텍스트: 페이지 단위 또는 토큰 기반 청킹
  └─ 임베딩 생성 및 FAISS 벡터스토어 생성
  ↓
섹션별 벡터스토어 캐시 저장

[질의응답 단계]
사용자 질문
  ↓
LLM 섹션 선택 (동적 라우팅)
  ↓
섹션 Re-ranking (관련성 점수 기반 재순위화)
  ↓
재순위화된 섹션별 표/텍스트 분리 검색 (벡터 유사도 검색)
  ↓
검색 결과 통합 및 점수 정렬
  ↓
스마트 청크 병합 (페이지 단위: 단순 연결, 토큰 기반: overlap 정보 활용)
  ↓
Context Swap (표는 raw_data 사용, 텍스트는 page_content 사용)
  ↓
표 분석 (Gemini로 질문 관련 정보 추출)
  ↓
대화 히스토리 포함 답변 생성
  ↓
품질 평가 및 재시도 (필요시)
  ↓
최종 답변 반환
```

## 📦 핵심 컴포넌트

### 1. `core/toc_processor.py` - 목차 처리
- **목차 감지**: PDF 처음 10페이지에서 목차 키워드 검색 (Gemini LLM 활용)
- **목차 파싱**: Gemini LLM으로 섹션명과 페이지 범위 추출
- **섹션 검증**: 페이지 범위 유효성 검사 및 자동 수정

### 2. `core/vision_processor.py` - Gemini Vision 처리
- **이미지 변환**: PyMuPDF로 PDF 페이지를 고화질 이미지로 변환 (DPI 200)
- **마크다운 변환**: Gemini Vision으로 이미지를 마크다운으로 변환
  - 복잡한 레이아웃 정확히 인식
  - 표는 `<table_summary>` 태그로 요약 포함
  - 완벽한 Markdown 구조 보존
- **페이지 단위 병렬 처리**: ThreadPoolExecutor로 최대 4개 페이지 동시 변환
  - API 호출 시간 최적화
  - 전체 처리 시간 단축
- **재시도 로직**: API 호출 실패 시 자동 재시도 (최대 3회, 지수 백오프)

### 3. `core/preprocessor.py` - 섹션 전처리
- **섹션 추출**: PyPDF2로 특정 페이지 범위만 추출
- **Gemini Vision 변환**: 각 페이지를 이미지로 변환 후 마크다운으로 변환
  - 페이지 단위 병렬 처리로 속도 향상
- **Dual Chunking 처리**: `chunk_markdown_with_dual_chunking()` 사용
  - 표: `summary`(검색용) + `raw_data`(원본) 분리 저장
  - 텍스트: 페이지 단위 또는 토큰 기반 청킹
- **임베딩**: Google Gemini Embeddings로 벡터 생성
- **벡터스토어**: FAISS 벡터스토어 생성 및 저장

### 4. `core/chunker.py` - 스마트 청킹 및 Dual Chunking
- **Dual Chunking 처리**: Gemini Vision 마크다운을 처리
  - `<table_summary>` 태그 추출 및 표 마크다운 분리
  - 표: `summary`(검색용) + `raw_data`(원본) 분리 저장
  - 텍스트: 일반 청킹 방식 적용
- **페이지 단위 청킹**: PDF를 페이지별로 분할하여 각 페이지를 하나의 청크로 처리
  - 원본 PDF의 실제 페이지 번호를 메타데이터에 저장
  - 페이지 단위로 정확한 위치 추적 가능
- **토큰 기반 청킹**: `tiktoken`으로 정확한 토큰 수 계산
  - Long Context 전략: 800 토큰, 150 토큰 오버랩
  - 오버랩 메타데이터: 각 청크의 이전/다음 청크와의 오버랩 정보 저장
- **스마트 병합**: 검색 시 연속된 청크를 정확히 병합
  - 페이지 단위: 단순 연결 (overlap 없음)
  - 토큰 기반: overlap 정보 활용한 정확한 병합

### 5. `core/searcher.py` - 검색 엔진
- **벡터 검색**: FAISS 유사도 검색 (`similarity_search_with_score`)
- **점수 변환**: 거리 점수를 유사도 점수로 변환 (0에 가까울수록 유사)
- **단순화된 검색**: 복잡한 BM25, RRF, Reranking 로직 제거

### 6. `core/rag_system.py` - RAG 시스템
- **섹션 선택**: Gemini LLM으로 질문과 관련된 섹션 선택
- **섹션 Re-ranking**: 선택된 섹션들을 관련성 점수(0-100)로 재순위화
  - LLM이 각 섹션의 제목과 질문의 관련성을 평가
  - 관련성 높은 섹션을 우선 처리
  - JSON 형식으로 점수와 이유 반환
- **표/텍스트 분리 병합**: 표와 텍스트 문서를 별도로 처리
- **청크 병합**: 청크 타입에 따라 다른 병합 방식 적용
  - 페이지 단위: 페이지 번호 기준으로 연속된 페이지 병합
  - 토큰 기반: chunk_index와 overlap 정보 활용한 병합
- **Context Swap**: 검색된 문서의 타입에 따라 다른 데이터 사용
  - 표: `metadata['raw_data']` 사용 (원본 표 마크다운)
  - 텍스트: `page_content` 사용
- **표 분석**: 검색된 표를 Gemini로 분석하여 질문 관련 정보 추출
- **답변 생성**: 대화 히스토리를 고려한 답변 생성

### 7. `core/quality_evaluator.py` - 품질 평가
- **LLM 기반 평가**: 답변의 관련성, 완전성, 정확성, 유용성 평가
- **재시도 트리거**: 품질이 낮으면 자동 재시도

## 🔧 기술 스택

### LLM & Embeddings
- **LLM**: Google Gemini 3 Flash Preview (`temperature=0`)
- **Vision Model**: Google Gemini 2.0 Flash Exp (이미지-마크다운 변환)
- **Embeddings**: Google Gemini Embeddings (`models/embedding-001`)

### PDF 처리
- **PyPDF2**: PDF 페이지 추출 및 섹션 분리
- **PyMuPDF (fitz)**: PDF 페이지를 고화질 이미지로 변환 (DPI 200)
- **PIL (Pillow)**: 이미지 객체 처리
- **Gemini Vision**: 이미지를 마크다운으로 변환
  - 복잡한 레이아웃 정확히 인식
  - 표는 `<table_summary>` 태그로 요약 포함

### 벡터 검색
- **FAISS**: 효율적인 유사도 검색
- **similarity_search_with_score**: 거리 기반 유사도 검색

### 병렬 처리
- **ThreadPoolExecutor**: 섹션 전처리 및 페이지 변환 병렬화
- **최대 4개 동시 처리**: 섹션 전처리와 페이지 변환 모두 병렬화

### 기타
- **tiktoken**: 정확한 토큰 수 계산 (토큰 기반 청킹 시)
- **Streamlit**: 웹 UI 프레임워크

## 📋 필수 요구사항

- Python 3.8 이상
- Google Gemini API Key (Vision API 사용)

## 🔧 설치 방법

### 1. 저장소 클론 및 이동
```bash
cd "/Users/gimdogyun/Desktop/임베딩_기반 2"
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는
# venv\Scripts\activate  # Windows
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일에 API 키를 추가하세요:

```env
GEMINI_API_KEY=your_google_api_key_here
```

**API 키 발급:**
- Google Gemini: [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 사용 방법

### 1. 애플리케이션 실행
```bash
streamlit run main.py --server.port 8053
```

### 2. 웹 브라우저에서 접속
- 자동으로 브라우저가 열립니다 (보통 http://localhost:8053)

### 3. 모집요강 PDF 업로드
- 사이드바에서 대학 입시 모집요강 PDF를 업로드하세요
- 목차 감지 및 섹션별 전처리가 자동으로 진행됩니다
- 처음 1회만 처리되며, 이후에는 캐시를 사용합니다

### 4. 입시 상담하기
- 화면 하단의 입력창에 입시 관련 질문을 입력하세요
- AI 입시 전문가가 업로드된 모집요강을 기반으로 답변합니다

**질문 예시:**
- "경희대학교 빅데이터응용학과 네오르네상스 전형으로 몇 명 뽑나요?"
- "이 대학의 학생부종합전형 지원 자격은?"
- "전형별 모집 인원을 비교해주세요"
- "논술전형 제출 서류는 무엇인가요?"
- "원서 접수 기간은 언제인가요?"

## 📊 Gemini Vision 기반 PDF 처리 상세

### PDF → 마크다운 변환 파이프라인

1. **이미지 변환 단계**
   - PyMuPDF로 PDF 페이지를 고화질 이미지로 변환 (DPI 200)
   - PIL Image 객체로 생성
   - 복잡한 레이아웃도 정확히 보존

2. **Gemini Vision 변환 단계 (병렬 처리)**
   - 각 페이지를 독립적으로 처리하여 병렬 실행
   - ThreadPoolExecutor로 최대 4개 페이지 동시 변환
   - Gemini Vision 모델에 이미지와 시스템 프롬프트 전송
   - 프롬프트 규칙:
     - Markdown 문법으로 정확히 표현
     - 표는 Markdown Table 형식으로 변환
     - **핵심**: 모든 표 위에 `<table_summary>표 요약</table_summary>` 태그 삽입
     - 머리말, 꼬리말, 페이지 번호 제외
   - 완벽한 Markdown 구조로 변환
   - 결과는 페이지 번호 순서대로 정렬

3. **Dual Chunking 처리 단계**
   - `<table_summary>` 태그 패턴 감지
   - 표 처리:
     - **검색용**: `summary` + 주변 텍스트 컨텍스트
     - **원본**: 전체 표 마크다운 (`raw_data`)
   - 텍스트 처리:
     - 페이지 단위 또는 토큰 기반 청킹

### 표 검색 및 분석 (Dual Chunking 전략)

1. **표/텍스트 분리 검색**
   - 각 섹션에서 표와 텍스트를 별도 벡터스토어로 분리
   - 각각 독립적으로 벡터 유사도 검색 수행
   - 섹션당 최대 30개 문서 검색
   - **검색 시**: 표의 `page_content`(summary + 컨텍스트)로 검색

2. **Context Swap**
   - 검색된 표 문서의 `metadata['raw_data']` 추출
   - 원본 표 마크다운을 컨텍스트에 포함

3. **Gemini 표 분석**
   - 원본 표 데이터를 Gemini로 분석
   - 질문과 관련된 정보만 추출
   - 구조화된 텍스트로 변환

4. **답변 생성**
   - 분석된 표 정보와 텍스트 문서를 통합
   - 최종 10개 문서를 LLM에 제공하여 답변 생성

### Dual Chunking 전략의 장점

- **검색 정확도 향상**: 자연어 요약으로 의미 기반 검색
- **답변 품질 향상**: 원본 표 데이터로 상세 정보 제공
- **비용 최적화**: 검색은 요약, 답변은 원본 사용
- **복잡한 레이아웃 처리**: 이미지 기반으로 레이아웃 정확히 인식

## 🎯 섹션 Re-ranking 상세

### Re-ranking 작동 원리

1. **섹션 선택**: LLM이 질문과 관련된 섹션 선택
2. **관련성 평가**: 선택된 섹션들을 LLM으로 관련성 평가
   - 각 섹션의 제목과 질문의 관련성을 분석
   - 관련성 점수(0-100) 부여
3. **재순위화**: 점수 기반으로 내림차순 정렬
4. **우선 처리**: 관련성 높은 섹션부터 검색 및 처리

### 관련성 점수 기준

- **90-100**: 매우 관련성 높음 (질문의 핵심 답변이 이 섹션에 있을 가능성 높음)
- **70-89**: 관련성 높음 (질문과 직접 관련된 정보가 포함됨)
- **50-69**: 관련성 보통 (간접적으로 관련된 정보가 포함될 수 있음)
- **30-49**: 관련성 낮음 (약간의 관련성만 있음)
- **0-29**: 관련성 매우 낮음 (거의 관련 없음)

### Re-ranking의 장점

- **검색 효율성 향상**: 관련성 높은 섹션을 우선 처리
- **답변 품질 향상**: 핵심 정보가 있는 섹션을 먼저 검색
- **처리 시간 단축**: 불필요한 섹션 처리 최소화

## ⚙️ 설정 (config.py)

### 기본 설정
```python
DEFAULT_LLM_MODEL = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
DEFAULT_EMBEDDING_MODEL = "models/embedding-001"
```

### 청킹 설정
```python
# 청킹 방식 선택
CHUNK_BY_PAGE = True          # True: 페이지 단위 청킹, False: 토큰 기반 청킹

# 토큰 기반 청킹 설정 (CHUNK_BY_PAGE=False일 때 사용)
CHUNK_SIZE_TOKENS = 800      # 청크 크기 (Long Context 전략)
CHUNK_OVERLAP_TOKENS = 150   # 오버랩 (약 19%)
```

### 검색 설정
```python
TOP_K_PER_SECTION = 30       # 섹션당 검색 문서 수
TOP_K_FINAL = 10             # 최종 선택 문서 수 (LLM에 제공)
```

### 재시도 설정
```python
DEFAULT_MAX_RETRIES = 3      # 최대 재시도 횟수
```

### 병렬 처리 설정
```python
MAX_WORKERS = 4              # 섹션 전처리 및 페이지 변환 병렬 처리 최대 개수
```

### 청킹 방식 비교

| 방식 | 장점 | 단점 | 사용 시기 |
|------|------|------|----------|
| **페이지 단위** | 정확한 페이지 번호 추적, 구조 보존, 단순함 | 페이지 크기에 따라 불균형 | 페이지 번호가 중요한 경우 |
| **토큰 기반** | 균일한 청크 크기, 문맥 보존 (overlap) | 페이지 번호 추적 어려움 | 긴 문맥이 중요한 경우 |

## 📁 프로젝트 구조

```
임베딩_기반 2/
├── main.py                  # 메인 Streamlit 애플리케이션
├── config.py                # 설정 파일
├── requirements.txt         # 필요한 Python 패키지
├── .env                     # 환경변수 (API 키)
├── README.md               # 프로젝트 설명 (이 파일)
├── RAG_PIPELINE.md         # 상세 파이프라인 문서
├── core/                   # 핵심 모듈
│   ├── __init__.py
│   ├── toc_processor.py    # 목차 처리
│   ├── vision_processor.py # Gemini Vision 기반 PDF 처리
│   ├── table_processor.py  # 표 처리 (레거시, Dual Chunking 로직 포함)
│   ├── preprocessor.py     # 섹션 전처리
│   ├── chunker.py         # 스마트 청킹 및 Dual Chunking
│   ├── searcher.py        # 검색 엔진
│   ├── rag_system.py      # RAG 시스템 (섹션 선택, Re-ranking 포함)
│   └── quality_evaluator.py # 품질 평가
├── prompts/               # 프롬프트 템플릿
│   └── pdf-rag.yaml      # RAG 프롬프트
└── .cache/               # 캐시 디렉토리 (자동 생성)
    ├── files/            # 업로드된 PDF 파일
    ├── embeddings/       # 임베딩 캐시
    └── toc_sections/    # 섹션 PDF 파일
```

## 🔍 주요 최적화 기법

### 1. 재임베딩 제거
- 검색된 문서를 직접 컨텍스트로 사용
- 불필요한 재임베딩 과정 제거

### 2. 컨텍스트 정렬
- 검색 점수 기반으로 문서 정렬
- 관련도 높은 문서를 우선 배치

### 3. 섹션 Re-ranking
- 선택된 섹션들을 관련성 점수로 재순위화
- 관련성 높은 섹션을 우선 처리하여 검색 효율성 향상

### 4. Dual Chunking 전략
- **표 처리**: 검색용 요약(summary) + 원본 데이터(raw_data) 분리
  - 검색: 자연어 요약으로 의미 기반 검색
  - 답변: 원본 표 마크다운으로 상세 정보 제공
- **Context Swap**: 검색된 표 문서의 `raw_data`를 컨텍스트에 포함

### 5. 스마트 청크 병합
- **페이지 단위**: 연속된 페이지를 단순 연결하여 병합
- **토큰 기반**: 오버랩 메타데이터를 활용한 정확한 병합
- 연속된 청크를 하나로 통합하여 문맥 보존

### 6. 다층 병렬 처리
- **섹션 전처리**: ThreadPoolExecutor로 최대 4개 섹션 동시 처리
- **페이지 변환**: 각 섹션 내에서 최대 4개 페이지 동시 변환
- 전체 처리 시간 대폭 단축

### 7. 캐싱
- Streamlit `@st.cache_resource`로 전처리 결과 캐싱
- 파일 수정 시간 기반 캐시 무효화
- 같은 PDF는 재처리하지 않음

## 💡 사용 팁

1. **초기 업로드**: PDF 전처리는 처음 1회만 수행되며, 이후에는 캐시를 사용합니다
2. **구체적 질문**: 명확하고 구체적인 질문이 더 정확한 답변을 얻을 수 있습니다
3. **표 데이터**: 모집단위별, 전형별 표 정보도 완벽하게 분석합니다
4. **대화 초기화**: 새로운 주제로 질문할 때는 "대화 초기화" 버튼을 클릭하세요
5. **재시도**: 답변 품질이 낮으면 자동으로 재시도합니다 (최대 3회)
6. **섹션 Re-ranking**: 관련 섹션이 여러 개일 때 자동으로 관련성 순으로 처리됩니다

## 🐛 문제 해결

### API 키 오류
```
Error: API key not found
```
→ `.env` 파일에 `GEMINI_API_KEY`가 올바르게 설정되었는지 확인하세요

### Gemini Vision API 오류
```
Error: API key not found
```
→ `.env` 파일에 `GEMINI_API_KEY`가 올바르게 설정되었는지 확인하세요
→ Gemini Vision API는 일반 Gemini API와 동일한 키를 사용합니다

### 이미지 변환 오류
```
⚠️ 페이지 N 이미지 변환 중 오류
```
→ PyMuPDF가 제대로 설치되었는지 확인: `pip install pymupdf`
→ PDF 파일이 손상되었을 수 있습니다

### 마크다운 변환 실패
→ Gemini Vision API 호출 실패 시 자동으로 재시도합니다 (최대 3회)
→ 네트워크 오류나 API 할당량 초과 시 재시도가 실패할 수 있습니다

### FAISS 설치 오류 (Mac M1/M2)
```bash
pip install faiss-cpu --no-cache
```

### 포트 충돌
```bash
# 기존 프로세스 종료
lsof -ti:8053 | xargs kill -9
```

## 📝 라이선스

이 프로젝트는 개인 학습 및 연구 목적으로 사용할 수 있습니다.

## 🙏 참고 자료

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Google Gemini Vision API](https://ai.google.dev/docs)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

## 📚 상세 문서

- **RAG_PIPELINE.md**: 전체 파이프라인 상세 설명
- **코드 주석**: 각 함수와 클래스에 상세한 주석 포함
