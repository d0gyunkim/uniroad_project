# 🎓 대학 입시 컨설턴트 (Gemini)

Google Gemini를 활용한 임베딩 기반 대학 입시 상담 시스템입니다.
**모든 대학**의 입시 모집요강 PDF를 업로드하여 정확한 입시 정보를 제공받을 수 있습니다.

## 🎨 네 가지 버전

| 버전 | 파일 | 특징 | 추천 |
|------|------|------|------|
| **고성능 모드** | `app.py` | 빠른 처리 (1-2분) | 일반 질문 |
| **Multi-Modal** | `app_multimodal.py` | 표 전용 처리 (2-3분) | 표 데이터 질문 |
| **멀티 에이전트** | `app_multi_agent.py` | 전체 분할 PDF (10-15초) | 포괄적 답변 |
| **라우팅 🌟** | `app_routed_agent.py` | 관련 문서만 (5-8초) | **효율+정확** |

자세한 내용:
- Multi-Modal: [`MULTIMODAL.md`](MULTIMODAL.md)
- 멀티 에이전트: [`MULTI_AGENT.md`](MULTI_AGENT.md)
- 라우팅 시스템: [`ROUTED_AGENT.md`](ROUTED_AGENT.md) ⭐

## 🚀 주요 기능

- **모집요강 분석**: 모든 대학의 입시 모집요강 PDF를 자동 분석
- **범용 입시 상담**: 어떤 대학이든 전형, 학과, 지원 자격, 일정 등 상세 안내
- **임베딩 기반 검색**: Google Gemini Embeddings를 사용한 의미 기반 정보 검색
- **실시간 답변**: 스트리밍 방식의 즉각적인 입시 상담
- **대화 기록**: 이전 질문과 답변 내용 유지 및 초기화 기능
- **Multi-Modal 지원**: 표 데이터 전용 처리로 정확도 극대화

## 📋 필수 요구사항

- Python 3.8 이상
- Google API Key (Gemini)

## 🔧 설치 방법

1. **저장소 클론 및 이동**
```bash
cd /Users/gimdogyun/Desktop/임베딩_기반
```

2. **가상환경 생성 및 활성화**
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는
# venv\Scripts\activate  # Windows
```

3. **필요한 패키지 설치**
```bash
pip install -r requirements.txt
```

4. **환경변수 설정**

`.env` 파일에 Google API Key를 추가하세요:

```env
GEMINI_API_KEY=your_google_api_key_here
```

또는

```env
GOOGLE_API_KEY=your_google_api_key_here
```

Google API Key는 [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급받을 수 있습니다.

## 🎯 사용 방법

1. **애플리케이션 실행**

**기본 모드 (빠름):**
```bash
streamlit run app.py
```

**Multi-Modal 모드 (표 전문):**
```bash
streamlit run app_multimodal.py
```

**멀티 에이전트 모드 (분할 PDF):**
```bash
streamlit run app_multi_agent.py
```

2. **웹 브라우저에서 접속**
   - 자동으로 브라우저가 열립니다 (보통 http://localhost:8501)

3. **모집요강 PDF 업로드**
   - 사이드바에서 대학 입시 모집요강 PDF를 업로드하세요
   - 파일 처리가 완료될 때까지 기다립니다 (최초 1회만, 1-3분)
   - 어떤 대학이든 가능 (서울대, 연세대, 고려대, 경희대 등)

4. **입시 상담하기**
   - 화면 하단의 입력창에 입시 관련 질문을 입력하세요
   - AI 입시 전문가가 업로드된 모집요강을 기반으로 답변합니다
   
**질문 예시:**
- "이 대학의 학생부종합전형 지원 자격은?"
- "경영학과 수시 모집 인원은 몇 명인가요?"
- "논술전형 제출 서류는 무엇인가요?"
- "원서 접수 기간은 언제인가요?"
- "전형별 모집 인원을 비교해주세요"

## 🏗️ 프로젝트 구조

```
임베딩_기반/
├── app.py                  # 메인 Streamlit 애플리케이션
├── requirements.txt        # 필요한 Python 패키지
├── .env                    # 환경변수 (API 키)
├── .gitignore             # Git 제외 파일
├── README.md              # 프로젝트 설명
├── prompts/
│   └── pdf-rag.yaml       # RAG 프롬프트 템플릿
└── .cache/                # 캐시 디렉토리 (자동 생성)
    ├── files/             # 업로드된 PDF 파일
    └── embeddings/        # 임베딩 캐시
```

## 🔑 주요 구성 요소

### 1. 문서 처리 파이프라인 (최고 성능 모드)

- **문서 로드**: PDFPlumberLoader를 사용한 PDF 파싱 (표 데이터 인식)
- **대용량 최적화**: 128페이지 대용량 문서 처리
- **텍스트 분할**: RecursiveCharacterTextSplitter로 청크 분할
  - 청크 크기: **3000자** (최대 문맥 보존)
  - 청크 중복: **600자** (정보 손실 완전 방지)
- **임베딩 생성**: Google Gemini Embeddings (embedding-001 모델)
- **벡터 저장소**: FAISS를 활용한 효율적인 검색
- **검색 방식**: MMR Advanced (Maximal Marginal Relevance)
  - 관련성과 다양성의 균형 유지
  - **최대 20개 문서 검색** (정확도 극대화)
  - **50개 후보 문서 풀** (최고 품질 보장)

### 2. LLM 모델 (최고 정확도 설정)

사용 중인 Gemini 모델:
- **gemini-2.0-flash-lite**: 빠른 응답 속도와 효율성 (고정)
- **Temperature**: 0 (최고 정확도, 일관된 문서 기반 답변)
- **컨텍스트 윈도우**: 20개 문서 (약 60,000자)

### 3. RAG (Retrieval-Augmented Generation)

- 문서에서 관련 정보 검색
- 검색된 컨텍스트 기반 답변 생성
- 스트리밍 방식의 실시간 응답

## 💡 사용 팁 (최고 성능 모드)

1. **초기 업로드**: 128페이지 PDF 처리 시 1-2분 정도 소요됩니다 (정확도를 위해 필요한 시간)
2. **최고 정확도**: 3000자 청크와 20개 문서 검색으로 최대한 정확한 답변을 제공합니다
3. **표 데이터**: 모집단위별, 전형별 표 정보도 완벽하게 분석합니다
4. **대화 초기화**: 새로운 주제로 질문할 때는 "대화 초기화" 버튼을 클릭하세요
5. **구체적 질문**: 명확하고 구체적인 질문이 더 정확한 답변을 얻을 수 있습니다
6. **문서 범위**: 문서에 없는 내용은 답변하지 않으므로, 문서 내용과 관련된 질문을 하세요
7. **성능 우선**: 업로드는 느려도 답변은 매우 정확하고 상세합니다

## 🐛 문제 해결

### API 키 오류
```
Error: API key not found
```
→ `.env` 파일에 `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`가 올바르게 설정되었는지 확인하세요

### 패키지 설치 오류
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### FAISS 설치 오류 (Mac M1/M2)
```bash
pip install faiss-cpu --no-cache
```

## 📝 라이선스

이 프로젝트는 개인 학습 및 연구 목적으로 사용할 수 있습니다.

## 🙏 참고 자료

- [LangChain Documentation](https://python.langchain.com/)
- [Google Gemini API](https://ai.google.dev/)
- [Streamlit Documentation](https://docs.streamlit.io/)

