# 📑 전체 RAG 파이프라인 구조

## 🏗️ 시스템 아키텍처 개요

```
[초기화 단계]
PDF 업로드
  ↓
목차 감지 및 파싱
  ↓
섹션별 병렬 전처리
  ├─ 표/텍스트 분리 (Upstage 우선 → Unstructured 폴백)
  ├─ 표 마크다운 변환 (Upstage) 또는 LLM 구조화 (Unstructured)
  ├─ 텍스트 토큰 기반 청킹 (600 토큰, 90 토큰 오버랩)
  └─ 임베딩 생성 및 FAISS 벡터스토어 생성
  ↓
섹션별 벡터스토어 저장 (캐시)

[질의응답 단계]
사용자 질문
  ↓
LLM 섹션 선택 (동적 라우팅)
  ↓
선택된 섹션별 벡터 검색 (MMR)
  ↓
검색 결과 통합 및 점수 정렬
  ↓
스마트 청크 병합 (overlap 정보 활용)
  ↓
대화 히스토리 포함 답변 생성
  ↓
품질 평가 및 재시도 (필요시)
  ↓
최종 답변 반환
```

---

## 📥 [초기화 단계] PDF 전처리 파이프라인

### 1단계: PDF 업로드 및 캐시 확인

```python
# main.py
uploaded_file → .cache/files/{파일명}.pdf 저장
파일 수정 시간 확인 → 캐시 무효화 여부 결정
```

**캐시 무효화 로직:**
- 파일 수정 시간이 변경되면 모든 캐시 삭제
- Upstage 캐시 파일 삭제
- Streamlit 캐시 무효화

---

### 2단계: 목차 감지 및 파싱

```python
# core/toc_processor.py
TOCProcessor.detect_toc_pages()
  - 처음 10페이지에서 목차 키워드 검색
  - "목차", "차례", "contents" 등 키워드 발견

TOCProcessor.parse_toc_structure()
  - LLM(Gemini)으로 목차 구조 추출
  - 섹션명 + 페이지 범위 파싱
  - 예: "전형별 모집인원 (18-20페이지)"
```

**결과:**
- 섹션 리스트: `[{"title": "...", "start_page": X, "end_page": Y}, ...]`
- 목차가 없으면 페이지 수 기반 자동 분할

---

### 3단계: 섹션별 병렬 전처리

```python
# core/preprocessor.py
SectionPreprocessor.preprocess_section()
```

#### 3-1. 섹션 PDF 추출
```python
PyPDF2로 특정 페이지 범위만 추출
→ .cache/toc_sections/section_{start}_{end}.pdf
```

#### 3-2. 표와 텍스트 분리 (하이브리드 방식)

**우선순위 1: Upstage Document Parse**
```python
# core/table_processor.py
TableProcessor.extract_tables_with_upstage()
  1. PyMuPDF로 표 위치 탐지 (find_tables())
  2. 표가 있는 페이지를 이미지로 변환
  3. Upstage Document Parse로 표 구조 추출
  4. htmltabletomd로 마크다운 변환
  5. 캐시 저장 (파일 수정 시간 포함)
```

**우선순위 2: Unstructured (폴백)**
```python
TableProcessor.extract_pdf_elements_multimodal()
  - infer_table_structure=True
  - 표를 Table 객체로 추출
```

**결과:**
- `texts`: 텍스트 리스트
- `tables`: 표 리스트 (마크다운 또는 원본)

#### 3-3. 표 구조화

**Upstage 표 (이미 마크다운):**
```python
# 마크다운 형식 확인 (| 기호 포함)
if "|" in table and "-" in table:
    → 그대로 사용 (LLM 변환 생략)
```

**Unstructured 표:**
```python
# LLM으로 구조화
TableProcessor.generate_table_summaries()
  - Gemini 2.5 Flash Lite
  - 마크다운 표 형식으로 변환
  - 구조 보존하면서 검색 최적화
```

#### 3-4. 텍스트 청킹

```python
# core/chunker.py
DocumentChunker.chunk_with_overlap_metadata()
  - 토큰 기반 청킹 (tiktoken)
  - 청크 크기: 600 토큰
  - 오버랩: 90 토큰 (15%)
  - overlap 메타데이터 저장 (병합용)
```

**청크 메타데이터:**
```python
{
  "content": "청크 내용",
  "chunk_index": 0,
  "start_pos": 0,
  "end_pos": 600,
  "overlap_prev": {"text": "...", "start": 0, "end": 0},
  "overlap_next": {"text": "...", "start": 510, "end": 600}
}
```

#### 3-5. Document 객체 생성

```python
# 표 Document
Document(
  page_content=table_markdown,
  metadata={
    'section_title': '...',
    'is_table': True  # ⭐ 표는 청킹하지 않음
  }
)

# 텍스트 청크 Document
Document(
  page_content=chunk_content,
  metadata={
    'section_title': '...',
    'chunk_index': 0,
    'overlap_prev_text': '...',
    'overlap_next_text': '...',
    'is_table': False
  }
)
```

#### 3-6. 임베딩 생성 및 벡터스토어 생성

```python
GoogleGenerativeAIEmbeddings(model="models/embedding-001")
  → 각 Document를 벡터로 변환

FAISS.from_documents(documents, embedding)
  → FAISS 벡터스토어 생성
  → 섹션별로 독립적인 벡터스토어 저장
```

**병렬 처리:**
```python
ThreadPoolExecutor(max_workers=4)
  → 최대 4개 섹션 동시 전처리
  → 처리 속도 향상
```

---

## 🔍 [질의응답 단계] RAG 파이프라인

### 1단계: 질문 분석 및 섹션 선택 (동적 라우팅)

```python
# core/rag_system.py
RAGSystem.find_relevant_sections()
```

**프로세스:**
1. LLM에 질문과 목차 전달
2. LLM이 관련 섹션 선택
3. 선택 근거 제공 (사고 과정)

**예시:**
```
질문: "경영회계계열 네오르네상스 전형 모집 인원은?"
→ 섹션 선택: "전형별 모집인원" (18-20페이지)
```

---

### 2단계: 섹션별 벡터 검색

```python
# core/searcher.py
SearchEngine.hybrid_search()
```

**검색 방식: MMR (Maximal Marginal Relevance)**
```python
vectorstore.as_retriever(
  search_type="mmr",
  search_kwargs={
    "k": 10,  # 각 섹션에서 10개 문서
    "fetch_k": 20,  # 후보 20개
    "lambda_mult": 0.8  # 관련성 우선 (80%)
  }
)
```

**특징:**
- 벡터 검색만 사용 (키워드 검색 제거)
- 관련성과 다양성의 균형
- 점수 보존: `[(Document, score), ...]`

---

### 3단계: 검색 결과 통합 및 정렬

```python
# core/rag_system.py
RAGSystem.merge_and_sort_docs()
```

**프로세스:**
1. 모든 섹션의 검색 결과 통합
2. 중복 제거 (섹션명 + chunk_index 기준)
3. 연속된 청크 병합 (overlap 정보 활용)
4. 점수 기반 정렬 (관련도 높은 순)
5. 상위 20개 선택

**청크 병합:**
```python
# 연속된 청크 (chunk_index가 연속) 병합
chunk_index: 0, 1, 2 → 하나로 병합
  - overlap 정보로 정확한 텍스트 복원
  - 중복 제거
```

---

### 4단계: 답변 생성 (대화 연속성 고려)

```python
# core/rag_system.py
RAGSystem.generate_answer()
```

**프로세스:**
1. 검색된 문서들을 컨텍스트로 구성
2. 이전 대화 히스토리 포함 (최근 3턴)
3. LLM에 전달하여 답변 생성

**컨텍스트 구성:**
```
[이전 대화 맥락]
학생: 경영회계계열 모집 인원은?
컨설턴트: 경영회계계열은...

[업로드된 대학 입시 모집요강]
문서 1. [전형별 모집인원] [표 데이터]
| 모집단위 | 네오르네상스전형 |
|---------|----------------|
| 경영회계계열 | 63명 |

문서 2. [전형별 모집인원]
경영회계계열은 경영학과와 회계학과로 구성...

[학생 질문]
경영회계계열 네오르네상스 전형 모집 인원은?
```

**LLM 설정:**
- 모델: Gemini 2.5 Flash Lite
- Temperature: 0 (정확도 우선)
- 프롬프트: `prompts/pdf-rag.yaml`

---

### 5단계: 품질 평가 및 재시도

```python
# core/quality_evaluator.py
QualityEvaluator.evaluate()
```

**평가 기준:**
- 관련성 (Relevance)
- 완전성 (Completeness)
- 정확성 (Accuracy)
- 유용성 (Usefulness)

**재시도 로직:**
```python
for attempt in range(1, max_retries + 1):
    answer = generate_answer(...)
    quality = evaluate_answer(...)
    
    if quality["is_acceptable"]:
        return answer  # ✅ 합격
    else:
        continue  # ⚠️ 재시도
```

**최대 재시도:** 3회 (기본값)

---

## 🔧 핵심 기술 스택

### LLM & Embedding
- **LLM**: Google Gemini 2.5 Flash Lite (temperature=0)
- **Embedding**: Google Gemini Embeddings (embedding-001)
- **용도**: 
  - 목차 파싱
  - 섹션 선택
  - 표 구조화 (Unstructured 표만)
  - 답변 생성
  - 품질 평가

### PDF 처리
- **Upstage Document Parse**: 표 구조 추출 (우선)
- **Unstructured**: 표/텍스트 분리 (폴백)
- **PyMuPDF**: 표 위치 탐지, 페이지 추출
- **PyPDF2**: 섹션 PDF 추출

### 벡터 검색
- **FAISS**: 고속 유사도 검색
- **MMR**: 관련성과 다양성의 균형
- **검색 방식**: 벡터 검색만 사용 (키워드 검색 제거)

### 청킹
- **방식**: 토큰 기반 (tiktoken)
- **크기**: 600 토큰
- **오버랩**: 90 토큰 (15%)
- **표**: 청킹하지 않음 (전체 저장)

### 병렬 처리
- **ThreadPoolExecutor**: 섹션 전처리 병렬화
- **최대 워커**: 4개

---

## 📊 데이터 흐름

### 초기화 단계
```
PDF 파일
  ↓
목차 인덱스: [{"title": "...", "start_page": X, "end_page": Y}, ...]
  ↓
섹션별 벡터스토어: {
  "18_20": {
    "vectorstore": FAISS,
    "documents": [Document, ...],
    "section": {...}
  },
  ...
}
```

### 질의응답 단계
```
질문: "경영회계계열 모집 인원은?"
  ↓
선택된 섹션: ["전형별 모집인원"]
  ↓
검색 결과: [(Document, score), ...]  # 10개
  ↓
통합 및 정렬: [Document, ...]  # 상위 20개
  ↓
컨텍스트: "문서 1. [전형별 모집인원] [표 데이터]..."
  ↓
답변: "경영회계계열의 네오르네상스 전형 모집 인원은 63명입니다."
```

---

## 🎯 주요 특징

### 1. 목차 기반 동적 라우팅
- 질문에 따라 관련 섹션만 선택
- 전체 문서 검색 불필요
- 효율성 및 정확도 향상

### 2. 하이브리드 표 처리
- Upstage 우선 (정확한 표 인식)
- Unstructured 폴백 (안정성)
- 마크다운 형식으로 검색 최적화

### 3. 스마트 청킹
- 토큰 기반 정확한 크기 제어
- 오버랩 메타데이터로 정확한 병합
- 표는 청킹하지 않아 구조 보존

### 4. 대화 연속성
- 이전 대화 히스토리 포함
- 자연스러운 대화 흐름 유지

### 5. 품질 보장
- LLM 기반 답변 품질 평가
- 자동 재시도 메커니즘

### 6. 성능 최적화
- 병렬 전처리
- 캐싱 (파일 수정 시간 기반 무효화)
- 벡터 검색만 사용 (빠른 속도)

---

## 💾 캐싱 전략

### Streamlit 캐시
```python
@st.cache_resource
def build_toc_index_and_preprocess(pdf_path, _cache_key, _file_mtime):
    # 파일 수정 시간이 변경되면 캐시 무효화
```

### Upstage 캐시
```python
# .cache/{파일명}_upstage.pickle
{
  'pdf_metainfo': {...},
  '_file_mtime': 1234567890  # 파일 수정 시간
}
```

### 캐시 무효화
- 파일 수정 시간 변경 시 자동 무효화
- 새 PDF 업로드 시 관련 캐시 삭제

---

## 🔄 전체 파이프라인 요약

### 초기화 (1회만)
1. PDF 업로드 → 파일 저장
2. 목차 감지 → 섹션 추출
3. 섹션별 병렬 전처리
   - 표/텍스트 분리
   - 표 구조화
   - 텍스트 청킹
   - 임베딩 생성
   - 벡터스토어 생성
4. 캐시 저장

### 질의응답 (실시간)
1. 질문 입력
2. 섹션 선택 (동적 라우팅)
3. 벡터 검색 (MMR)
4. 결과 통합 및 정렬
5. 청크 병합
6. 답변 생성 (대화 히스토리 포함)
7. 품질 평가
8. 재시도 (필요시)
9. 답변 반환

---

## 📈 성능 지표

- **초기화 시간**: 1-2분 (128페이지 기준)
- **질의응답 시간**: 5-10초
- **검색 정확도**: 벡터 검색 + MMR로 향상
- **표 인식률**: Upstage 사용 시 대폭 향상
- **답변 품질**: 자동 평가 및 재시도로 보장

