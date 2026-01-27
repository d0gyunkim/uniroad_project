# 📑 목차 기반 동적 라우팅 RAG 시스템 - 모듈화 버전

## 🏗️ 프로젝트 구조

```
임베딩_기반 2/
├── main.py                    # 메인 실행 파일 (Streamlit 앱)
├── config.py                  # 설정 파일 (환경 변수, 기본값)
├── core/                      # 핵심 모듈 디렉토리
│   ├── __init__.py           # 모듈 초기화
│   ├── toc_processor.py      # 목차 처리 (감지, 파싱)
│   ├── chunker.py            # 문서 청킹 (토큰 기반, overlap 메타데이터)
│   ├── table_processor.py    # 표 처리 (추출, 변환)
│   ├── searcher.py           # 검색 엔진 (키워드, 하이브리드)
│   ├── preprocessor.py       # 섹션 전처리 (임베딩, 벡터스토어)
│   ├── rag_system.py         # RAG 시스템 (질의응답 파이프라인)
│   └── quality_evaluator.py  # 품질 평가
├── prompts/                   # 프롬프트 템플릿
│   └── pdf-rag.yaml
└── requirements.txt           # 의존성 패키지
```

## 📦 모듈 설명

### 1. `config.py`
- 환경 변수 및 기본 설정값 관리
- API Key 설정
- 청킹, 검색, 재시도 등 설정값

### 2. `core/toc_processor.py` - TOCProcessor
- 목차 페이지 감지
- 목차 구조 파싱 (LLM 사용)
- 기본 섹션 생성 (목차 없을 때)
- 페이지 범위 검증

### 3. `core/chunker.py` - DocumentChunker
- 토큰 기반 스마트 청킹
- Overlap 메타데이터 저장
- 청크 병합 기능

### 4. `core/table_processor.py` - TableProcessor
- PDF에서 표 추출 (unstructured)
- 표와 텍스트 분류
- 표를 구조화된 텍스트로 변환 (LLM)

### 5. `core/searcher.py` - SearchEngine
- 키워드 검색 (한글 형태소 분석)
- 하이브리드 검색 (벡터 + 키워드)
- 점수 계산 및 정렬

### 6. `core/preprocessor.py` - SectionPreprocessor
- PDF 섹션 추출
- 표/텍스트 분리 및 처리
- 임베딩 생성 및 FAISS 벡터스토어 생성

### 7. `core/rag_system.py` - RAGSystem
- 관련 섹션 선택 (동적 라우팅)
- 검색 결과 병합 및 정렬
- 답변 생성

### 8. `core/quality_evaluator.py` - QualityEvaluator
- 답변 품질 평가 (LLM)
- 합격/불합격 판정

### 9. `main.py`
- Streamlit 앱 진입점
- UI 로직
- 전체 파이프라인 오케스트레이션

## 🚀 실행 방법

```bash
streamlit run main.py --server.port 8053
```

## 🔧 설정 변경

`config.py` 파일에서 다음 설정을 변경할 수 있습니다:

- `DEFAULT_LLM_MODEL`: LLM 모델명
- `CHUNK_SIZE_TOKENS`: 청크 크기 (기본값: 600)
- `CHUNK_OVERLAP_TOKENS`: 오버랩 크기 (기본값: 90)
- `VECTOR_SEARCH_WEIGHT`: 벡터 검색 가중치 (기본값: 0.7)
- `KEYWORD_SEARCH_WEIGHT`: 키워드 검색 가중치 (기본값: 0.3)
- `MAX_WORKERS`: 병렬 처리 최대 개수 (기본값: 4)

## 📝 모듈화의 장점

1. **유지보수성**: 각 기능이 독립적인 클래스로 분리되어 수정이 용이
2. **가독성**: 코드 구조가 명확하고 이해하기 쉬움
3. **재사용성**: 각 모듈을 다른 프로젝트에서도 활용 가능
4. **테스트 용이성**: 각 클래스를 독립적으로 테스트 가능
5. **확장성**: 새로운 기능 추가 시 해당 모듈만 수정하면 됨

## 🔄 기존 파일과의 관계

- `app_toc_routing.py`: 기존 단일 파일 (참고용으로 유지)
- `main.py`: 새로운 모듈화된 실행 파일 (사용 권장)

