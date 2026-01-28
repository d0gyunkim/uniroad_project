# 📑 목차 기반 동적 라우팅 RAG 시스템

Google Gemini를 활용한 **목차 기반 동적 라우팅 RAG (Retrieval-Augmented Generation)** 시스템입니다. 대학 입시 모집요강 PDF를 자동으로 분석하여 정확한 입시 정보를 제공합니다.

## 🎯 핵심 특징

- **📋 목차 자동 감지 및 파싱**: Gemini LLM으로 PDF 목차를 자동 인식하여 섹션별 구조화 (병렬 처리)
- **🎯 동적 섹션 선택**: 질문에 따라 관련 섹션만 선택하여 효율성 극대화
- **👁️ Gemini Vision 기반 PDF 처리**: PDF 페이지를 이미지로 변환하여 Gemini Vision으로 마크다운 변환
  - 복잡한 레이아웃 정확히 인식
  - 표와 텍스트를 완벽하게 구조화
- **⚡ 다층 병렬 처리**: 섹션 전처리와 페이지 변환을 병렬로 수행하여 속도 극대화
- **📄 페이지 단위 청킹**: 각 페이지를 하나의 청크로 처리하여 정확한 페이지 번호 추적
- **📊 Dual Chunking 전략**: 표는 검색용 요약 + 원본 데이터로 분리 저장
  - 검색: 자연어 요약으로 의미 기반 검색
  - 답변: 원본 표 데이터로 상세 정보 제공
- **🔍 표/텍스트 분리 검색**: 표와 텍스트를 별도로 검색하여 정확도 향상 (병렬 처리)
- **✂️ 동적 컷오프 (Elbow Method)**: 관련성 낮은 문서를 자동으로 제거하여 TTFT 향상 및 할루시네이션 방지
- **⚡ 스트리밍 답변**: 실시간으로 답변을 생성하여 Time-to-First-Token 최적화
- **✅ 품질 평가 및 재시도**: LLM 기반 답변 품질 평가 및 자동 재시도
- **💬 대화 연속성**: 이전 대화 맥락을 고려한 자연스러운 답변
- **🗄️ Supabase 통합**: PostgreSQL + pgvector 기반 벡터 데이터베이스 지원
  - **완전한 Supabase 기반 RAG 시스템**: 로컬 FAISS 대신 Supabase를 기본 저장소로 사용
  - 전처리된 PDF 데이터를 체계적으로 DB에 저장
  - 문서, 섹션, 청크 계층 구조로 관리
  - 동적 라우팅: Supabase에서 섹션 목록 조회 및 선택
  - 벡터 유사도 검색: Supabase RPC 함수를 통한 효율적인 검색

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
  └─ 임베딩 생성 및 Supabase 업로드
  ↓
Supabase 데이터베이스에 저장
  ├─ documents 테이블: 문서 메타데이터
  ├─ document_sections 테이블: 섹션 정보
  └─ document_chunks 테이블: 청크 + 임베딩 벡터

[질의응답 단계]
사용자 질문 + 학교 이름
  ↓
Supabase에서 섹션 목록 조회
  ↓
LLM 섹션 선택 (동적 라우팅)
  ↓
Supabase RPC 함수로 벡터 유사도 검색 (선택된 섹션 필터링)
  ↓
검색 결과 통합 및 점수 정렬
  ↓
스마트 청크 병합 (페이지 단위: 단순 연결, 토큰 기반: overlap 정보 활용)
  ↓
동적 컷오프 (Elbow Method) 적용
  - 상위 5개 문서는 무조건 유지
  - 점수 차이 0.15 이상인 지점에서 컷오프
  - 관련성 낮은 문서 제거
  ↓
Context Swap (표는 raw_data 사용, 텍스트는 page_content 사용)
  ↓
대화 히스토리 포함 답변 생성 (스트리밍)
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
- **SearchEngine**: 로컬 FAISS 기반 검색 (레거시 지원)
- **SupabaseSearcher**: Supabase 기반 벡터 검색 (기본 사용)
  - Supabase RPC `match_document_chunks` 함수 호출
  - `school_name`과 `section_id`로 필터링
  - Context Swap: 반환된 Document의 `page_content`에 `raw_data` 사용
  - 메타데이터에 `page_number`, `score`, `chunk_type`, `section_title` 포함
  - 임베딩 벡터로 유사도 검색 수행

### 6. `core/rag_system.py` - RAG 시스템
- **Supabase 통합**: Supabase 클라이언트 및 임베딩 모델 자동 초기화
- **`_get_relevant_sections`**: Supabase에서 학교별 섹션 목록 조회
- **`find_relevant_sections`**: Gemini LLM으로 질문과 관련된 섹션 선택
  - Supabase에서 섹션 목록 자동 조회 (로컬 파일 불필요)
  - 동적 라우팅: 질문 분석 후 관련 섹션만 선택
- **`retrieve`**: SupabaseSearcher를 사용한 벡터 유사도 검색
  - 선택된 `section_id`로 필터링된 검색
  - `school_name`으로 학교별 데이터 분리
- **`answer`**: 전체 RAG 파이프라인 통합 메서드
  - 동적 라우팅 → Supabase 검색 → 문서 병합 → Elbow Method → 답변 생성
  - `school_name` 필수 인자
  - 스트리밍 모드 지원
- **표/텍스트 분리 병합**: 표와 텍스트 문서를 별도로 처리
- **청크 병합**: 청크 타입에 따라 다른 병합 방식 적용
  - 페이지 단위: 페이지 번호 기준으로 연속된 페이지 병합
  - 토큰 기반: chunk_index와 overlap 정보 활용한 병합
- **동적 컷오프 (Elbow Method)**: 관련성 낮은 문서를 자동으로 제거
  - 상위 5개 문서는 무조건 유지 (안전장치)
  - 점수 차이가 0.15 이상인 지점에서 컷오프
  - TTFT 향상 및 할루시네이션 방지
- **Context Swap**: 검색된 문서의 타입에 따라 다른 데이터 사용
  - 표: `metadata['raw_data']` 사용 (원본 표 마크다운, 별도 분석 없이 직접 사용)
  - 텍스트: `page_content` 사용
- **답변 생성**: 대화 히스토리를 고려한 답변 생성
  - 스트리밍 모드 지원: 실시간으로 답변 청크 생성
  - Time-to-First-Token 최적화

### 7. `core/quality_evaluator.py` - 품질 평가
- **LLM 기반 평가**: 답변의 관련성, 완전성, 정확성, 유용성 평가
- **재시도 트리거**: 품질이 낮으면 자동 재시도

### 8. `core/supabase_uploader.py` - Supabase 업로더
- **데이터베이스 마이그레이션**: FAISS 로컬 저장소에서 Supabase로 전환
- **계층적 데이터 저장**: 문서 → 섹션 → 청크 구조로 체계적 관리
- **배치 처리 최적화**: 임베딩 생성 및 청크 삽입을 배치로 처리하여 효율성 극대화
- **Dual Chunking 지원**: 검색용 `content`와 답변용 `raw_data` 분리 저장
- **4단계 업로드 프로세스**:
  1. `documents` 테이블에 문서 등록 (school_name, filename, metadata)
  2. `document_sections` 테이블에 섹션 등록 및 section_map 생성
  3. 배치 임베딩 생성 (GoogleGenerativeAIEmbeddings)
  4. `document_chunks` 테이블에 청크 등록 (100개 단위 배치)

## 🔧 기술 스택

### LLM & Embeddings
- **LLM**: Google Gemini 3 Flash Preview (`temperature=0`)
- **Vision Model**: Google Gemini 2.0 Flash Exp (이미지-마크다운 변환)
- **Embeddings**: Google Gemini Embeddings (`models/gemini-embedding-001`, 3072차원)

### PDF 처리
- **PyPDF2**: PDF 페이지 추출 및 섹션 분리
- **PyMuPDF (fitz)**: PDF 페이지를 고화질 이미지로 변환 (DPI 200)
- **PIL (Pillow)**: 이미지 객체 처리
- **Gemini Vision**: 이미지를 마크다운으로 변환
  - 복잡한 레이아웃 정확히 인식
  - 표는 `<table_summary>` 태그로 요약 포함

### 벡터 검색
- **Supabase (pgvector)**: PostgreSQL 기반 벡터 데이터베이스 (기본 사용)
  - 3072차원 임베딩 벡터 저장 (Gemini Embeddings)
  - RPC 함수 `match_document_chunks`를 통한 벡터 유사도 검색
  - `school_name`과 `section_id`로 필터링 지원
  - 확장 가능한 클라우드 기반 솔루션
  - Context Swap: 검색 시 `raw_data` 자동 사용
- **FAISS**: 로컬 저장소 (레거시 지원, Supabase 마이그레이션 완료)

### 병렬 처리
- **ThreadPoolExecutor**: 섹션 전처리 및 페이지 변환 병렬화
- **최대 4개 동시 처리**: 섹션 전처리와 페이지 변환 모두 병렬화

### 기타
- **tiktoken**: 정확한 토큰 수 계산 (토큰 기반 청킹 시)
- **Streamlit**: 웹 UI 프레임워크

## 📋 필수 요구사항

- Python 3.8 이상
- Google Gemini API Key (Vision API 사용)
- Supabase 계정 및 프로젝트 (Supabase 업로더 사용 시)

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
# Google Gemini API
GEMINI_API_KEY=your_google_api_key_here

# Supabase (Supabase 업로더 사용 시)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

**API 키 발급:**
- Google Gemini: [Google AI Studio](https://makersuite.google.com/app/apikey)
- Supabase: [Supabase Dashboard](https://app.supabase.com/) → 프로젝트 설정 → API

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

## 🗄️ Supabase 기반 RAG 시스템

### 개요

이 시스템은 **Supabase (PostgreSQL + pgvector)**를 기본 벡터 저장소로 사용합니다. 로컬 FAISS 대신 클라우드 기반 데이터베이스를 사용하여 확장성과 유지보수성을 크게 향상시켰습니다.

### 주요 특징

1. **완전한 Supabase 통합**
   - 모든 벡터 검색이 Supabase RPC 함수를 통해 수행
   - 로컬 파일 시스템 의존성 제거
   - 클라우드 기반 확장 가능한 아키텍처

2. **동적 라우팅 (Supabase 기반)**
   - Supabase `document_sections` 테이블에서 섹션 목록 자동 조회
   - LLM이 질문 분석 후 관련 섹션만 선택
   - `school_name`으로 학교별 데이터 완전 분리

3. **효율적인 벡터 검색**
   - Supabase RPC `match_document_chunks` 함수 사용
   - `school_name`과 `section_id`로 필터링된 검색
   - Context Swap: 검색 시 자동으로 `raw_data` 사용

4. **계층적 데이터 구조**
   ```
   documents (학교별 문서)
     └── document_sections (섹션 정보)
           └── document_chunks (청크 + 임베딩 벡터)
   ```

### 5. Supabase에 데이터 업로드

**⚠️ 중요**: RAG 시스템이 Supabase를 기본으로 사용하므로, PDF 데이터를 먼저 Supabase에 업로드해야 합니다.

#### 방법 1: ingest_pdf.py 스크립트 사용 (권장)

```bash
python scripts/ingest_pdf.py
```

스크립트 내에서 다음 설정을 수정하세요:
```python
PDF_FILE_PATH = "테스트_폴더/2026학년도_고려대(서울)_입학전형시행계획(2025.05).pdf"
SCHOOL_NAME = "고려대학교"
```

#### 방법 2: Python 코드로 직접 업로드

```python
from core.supabase_uploader import upload_to_supabase

# 전처리된 데이터 준비
processed_data = {
    "toc_sections": [
        {"title": "1. 모집요강", "start_page": 1, "end_page": 10},
        {"title": "2. 전형방법", "start_page": 11, "end_page": 20}
    ],
    "chunks": [Document(...), Document(...), ...]  # LangChain Document 리스트
}

# Supabase에 업로드
document_id = upload_to_supabase(
    school_name="고려대학교",
    file_path="/path/to/file.pdf",
    processed_data=processed_data
)
```

### 6. Supabase 기반 RAG 시스템 사용

데이터 업로드 후, Supabase 기반 RAG 시스템을 사용할 수 있습니다:

```python
from core.rag_system import RAGSystem

# RAG 시스템 초기화 (Supabase 자동 연결)
rag_system = RAGSystem()

# 답변 생성 (일반 모드)
result = rag_system.answer(
    question="고려대학교 수시 전형은 어떻게 되나요?",
    school_name="고려대학교",  # 필수
    conversation_history=[],
    stream=False
)

print(result["answer"])
print(f"선택된 섹션: {len(result['selected_sections'])}개")
print(f"근거 문서: {len(result['evidence'])}개")

# 답변 생성 (스트리밍 모드)
for chunk in rag_system.answer(
    question="고려대학교 수시 전형은 어떻게 되나요?",
    school_name="고려대학교",
    stream=True
):
    print(chunk, end="", flush=True)
```

**업로드 프로세스:**
1. **문서 등록**: `documents` 테이블에 학교명, 파일명, 메타데이터 저장
2. **섹션 등록**: `document_sections` 테이블에 목차 섹션 정보 저장
3. **임베딩 생성**: 모든 청크의 임베딩을 배치로 생성 (3072차원, Gemini Embeddings)
4. **청크 등록**: `document_chunks` 테이블에 청크 데이터 저장 (100개 단위 배치)
   - Dual Chunking: `content`(검색용)와 `raw_data`(답변용) 분리 저장
   - 섹션 ID 자동 매핑
   - 페이지 번호 및 청크 타입 저장
   - 임베딩 벡터는 pgvector 형식으로 자동 저장

**Supabase 테이블 스키마:**
- `documents`: `id`, `school_name`, `filename`, `metadata` (jsonb)
- `document_sections`: `id`, `document_id` (FK), `section_name`, `page_start`, `page_end`
- `document_chunks`: `id`, `document_id` (FK), `section_id` (FK), `content`, `raw_data`, `embedding` (vector 3072), `page_number`, `chunk_type`

**Supabase RPC 함수:**
- `match_document_chunks`: 벡터 유사도 검색 함수
  - 파라미터: `query_embedding` (vector), `filter_school_name` (text), `filter_section_id` (int, 선택), `match_threshold` (float), `match_count` (int)
  - 반환: `id`, `content`, `raw_data`, `page_number`, `chunk_type`, `section_id`, `document_id`, `section_name`, `similarity` (float)

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
   - 원본 표 마크다운을 컨텍스트에 직접 포함
   - 별도 LLM 호출 없이 원본 데이터 사용 (속도 최적화)

3. **동적 컷오프 적용**
   - Elbow Method 기반으로 관련성 낮은 문서 제거
   - 상위 5개는 무조건 유지
   - 점수 차이 0.15 이상인 지점에서 컷오프

4. **답변 생성 (스트리밍)**
   - 원본 표 데이터와 텍스트 문서를 통합
   - 동적 컷오프로 필터링된 문서를 LLM에 제공
   - 스트리밍 방식으로 실시간 답변 생성

### Dual Chunking 전략의 장점

- **검색 정확도 향상**: 자연어 요약으로 의미 기반 검색
- **답변 품질 향상**: 원본 표 데이터로 상세 정보 제공
- **비용 최적화**: 검색은 요약, 답변은 원본 사용
- **복잡한 레이아웃 처리**: 이미지 기반으로 레이아웃 정확히 인식

## ✂️ 동적 컷오프 (Elbow Method) 상세

### 동적 컷오프 작동 원리

1. **점수 기반 정렬**: 검색된 문서들을 유사도 점수로 내림차순 정렬
2. **안전장치 적용**: 상위 5개 문서는 무조건 유지 (min_k=5)
3. **점수 차이 계산**: 각 문서와 다음 문서 간의 점수 차이 계산
4. **컷오프 지점 탐지**: 점수 차이가 임계값(0.15) 이상인 지점에서 컷오프
5. **문서 필터링**: 컷오프 지점 이후의 문서 제거

### 컷오프 예시

```
문서 점수: [0.95, 0.92, 0.89, 0.87, 0.85, 0.45, 0.40, 0.35, ...]
점수 차이: [0.03, 0.03, 0.02, 0.02, 0.40, 0.05, 0.05, ...]
                    ↑
            여기서 점수 차이 0.40 > 0.15 (임계값)
            → 5번째 문서까지 유지, 6번째부터 제거
```

### 동적 컷오프의 장점

- **TTFT 향상**: 관련성 낮은 문서 제거로 LLM 입력 토큰 감소
- **할루시네이션 방지**: 노이즈 문서 제거로 답변 정확도 향상
- **비용 절감**: 불필요한 토큰 처리 감소
- **자동 최적화**: 질문별로 적절한 문서 수 자동 결정

## ⚙️ 설정 (config.py)

### 기본 설정
```python
DEFAULT_LLM_MODEL = "gemini-3-flash-preview"  # Gemini 3 Flash Preview
DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"  # Gemini Embeddings (3072차원)
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
임베딩_기반/
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
│   ├── preprocessor.py     # 섹션 전처리
│   ├── chunker.py         # 스마트 청킹 및 Dual Chunking
│   ├── searcher.py        # 검색 엔진 (SupabaseSearcher 포함)
│   ├── rag_system.py      # RAG 시스템 (Supabase 통합)
│   ├── quality_evaluator.py # 품질 평가
│   └── supabase_uploader.py # Supabase 업로더
├── scripts/                # 유틸리티 스크립트
│   ├── ingest_pdf.py      # PDF 수집 및 Supabase 업로드
│   ├── test_embedding.py  # 임베딩 모델 테스트
│   └── test_rag_supabase.py # Supabase RAG 시스템 테스트
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

### 3. 동적 컷오프 (Elbow Method)
- 관련성 낮은 문서를 자동으로 제거
- 상위 5개는 무조건 유지, 점수 차이 0.15 이상인 지점에서 컷오프
- TTFT 향상 및 할루시네이션 방지

### 4. 스트리밍 답변
- 실시간으로 답변 청크 생성
- Time-to-First-Token 최적화
- 사용자 경험 향상

### 5. Dual Chunking 전략
- **표 처리**: 검색용 요약(summary) + 원본 데이터(raw_data) 분리
  - 검색: 자연어 요약으로 의미 기반 검색
  - 답변: 원본 표 마크다운으로 상세 정보 제공
- **Context Swap**: 검색된 표 문서의 `raw_data`를 컨텍스트에 포함

### 6. 스마트 청크 병합
- **페이지 단위**: 연속된 페이지를 단순 연결하여 병합
- **토큰 기반**: 오버랩 메타데이터를 활용한 정확한 병합
- 연속된 청크를 하나로 통합하여 문맥 보존

### 7. 다층 병렬 처리
- **섹션 전처리**: ThreadPoolExecutor로 최대 4개 섹션 동시 처리
- **페이지 변환**: 각 섹션 내에서 최대 4개 페이지 동시 변환
- 전체 처리 시간 대폭 단축

### 8. 캐싱
- Streamlit `@st.cache_resource`로 전처리 결과 캐싱
- 파일 수정 시간 기반 캐시 무효화
- 같은 PDF는 재처리하지 않음

### 9. Supabase 통합 (완전한 마이그레이션 완료)
- **기본 저장소**: 로컬 FAISS 대신 Supabase를 기본 벡터 저장소로 사용
- **계층적 데이터 구조**: 문서 → 섹션 → 청크 3단계 구조
- **배치 처리 최적화**: 임베딩 생성 및 청크 삽입을 배치로 처리
- **Dual Chunking 지원**: 검색용 `content`와 답변용 `raw_data` 분리 저장
- **자동 섹션 매핑**: 섹션 이름 기반으로 section_id 자동 매핑
- **동적 라우팅**: Supabase에서 섹션 목록 조회 후 LLM으로 선택
- **벡터 검색**: Supabase RPC 함수를 통한 효율적인 유사도 검색
- **Context Swap**: 검색 시 자동으로 `raw_data` 사용
- **에러 처리**: 각 단계별 상세한 에러 처리 및 진행 상황 출력

## 💡 사용 팁

1. **초기 업로드**: PDF 전처리는 처음 1회만 수행되며, 이후에는 캐시를 사용합니다
2. **구체적 질문**: 명확하고 구체적인 질문이 더 정확한 답변을 얻을 수 있습니다
3. **표 데이터**: 모집단위별, 전형별 표 정보도 완벽하게 분석합니다
4. **대화 초기화**: 새로운 주제로 질문할 때는 "대화 초기화" 버튼을 클릭하세요
5. **재시도**: 답변 품질이 낮으면 자동으로 재시도합니다 (최대 3회)
6. **동적 컷오프**: 관련성 낮은 문서는 자동으로 제거되어 더 빠르고 정확한 답변을 제공합니다
7. **스트리밍 답변**: 답변이 실시간으로 생성되어 즉각적인 피드백을 받을 수 있습니다
8. **Supabase 통합 (완료)**: 
   - FAISS 로컬 저장소에서 Supabase로 완전히 마이그레이션 완료
   - 확장 가능한 클라우드 기반 솔루션
   - 동적 라우팅과 벡터 검색이 모두 Supabase 기반으로 동작
   - `school_name`으로 학교별 데이터 완전 분리

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

### Supabase 연결 오류
```
ValueError: Supabase 환경 변수가 설정되지 않았습니다.
```
→ `.env` 파일에 `SUPABASE_URL`과 `SUPABASE_KEY`가 올바르게 설정되었는지 확인하세요
→ Supabase 프로젝트의 API 설정에서 URL과 anon key를 확인하세요

### Supabase 임베딩 차원 오류
```
⚠️ 임베딩 차원이 예상과 다릅니다: XXX (예상: 768)
```
→ Google Gemini Embeddings 모델(`models/gemini-embedding-001`)은 3072차원을 사용합니다
→ Supabase의 `document_chunks` 테이블의 `embedding` 컬럼이 `vector(3072)` 타입인지 확인하세요
→ 기존 768차원 컬럼이 있다면 마이그레이션이 필요합니다

### 섹션 매핑 실패
```
⚠️ 섹션 'XXX'에 대한 ID를 찾을 수 없습니다.
```
→ 청크의 `metadata['section_title']`이 `toc_sections`의 `title`과 정확히 일치하는지 확인하세요
→ 섹션 등록이 성공적으로 완료되었는지 확인하세요

### Supabase RPC 함수 오류
```
❌ Supabase 검색 중 오류: function match_document_chunks does not exist
```
→ Supabase에 `match_document_chunks` RPC 함수가 생성되어 있는지 확인하세요
→ 함수는 `query_embedding`, `filter_school_name`, `filter_section_id`, `match_threshold`, `match_count` 파라미터를 받아야 합니다
→ 반환값에 `raw_data`, `section_name` 필드가 포함되어야 합니다

## 📝 라이선스

이 프로젝트는 개인 학습 및 연구 목적으로 사용할 수 있습니다.

## 🙏 참고 자료

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Google Gemini Vision API](https://ai.google.dev/docs)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## 📚 상세 문서

- **RAG_PIPELINE.md**: 전체 파이프라인 상세 설명
- **코드 주석**: 각 함수와 클래스에 상세한 주석 포함
