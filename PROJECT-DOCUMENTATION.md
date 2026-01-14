# 입시코디 AI - 프로젝트 전체 문서

**대학 입시 상담 AI 시스템**  
RAG(Retrieval Augmented Generation) 기반 지능형 챗봇

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택](#기술-스택)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [핵심 기능](#핵심-기능)
5. [RAG 알고리즘](#rag-알고리즘)
6. [데이터 파이프라인](#데이터-파이프라인)
7. [프로젝트 구조](#프로젝트-구조)
8. [API 명세](#api-명세)
9. [데이터베이스 스키마](#데이터베이스-스키마)
10. [실행 방법](#실행-방법)

---

## 🎯 프로젝트 개요

### 목적
대학 입시 관련 질문에 **공식 문서 기반**으로 정확한 답변을 제공하는 AI 챗봇

### 핵심 기능
1. **일반 채팅 모드** (흰 박스)
   - GPT 일반 지식 기반 답변
   - 친근한 상담 톤

2. **RAG 모드** (파란 박스)
   - 업로드된 공식 문서 기반 답변
   - 출처 표시
   - 정확한 정보 제공

3. **관리자 페이지**
   - PDF 파일 업로드
   - 자동 OCR 처리 (LlamaParse)
   - AI 문서 분류
   - 자동 임베딩 및 저장

---

## 🛠 기술 스택

### 백엔드
```
- Python 3.9
- FastAPI (웹 프레임워크)
- Uvicorn (ASGI 서버)
```

### 프론트엔드
```
- React 18
- TypeScript
- Vite (빌드 도구)
- TailwindCSS (스타일링)
- React Router (라우팅)
```

### AI/ML
```
- OpenAI GPT-4o-mini (대화 생성, 문서 분류)
- OpenAI text-embedding-3-small (임베딩 생성)
- LlamaParse (PDF OCR, 표 구조 보존)
- LangChain (텍스트 청킹)
```

### 데이터베이스
```
- Supabase (PostgreSQL + pgvector)
- pgvector extension (벡터 검색)
```

### 개발 도구
```
- Git
- Cursor IDE
- Python venv
- npm
```

---

## 🏗 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                         사용자                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                  React Frontend (포트 5173)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  ChatPage    │  │  AdminPage   │  │  API Client  │       │
│  │  (채팅 UI)    │  │  (업로드 UI)  │  │  (Axios)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (Proxy: /api → :8000)
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (포트 8000)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Routers                                              │   │
│  │  - /api/chat        (채팅)                           │   │
│  │  - /api/upload      (파일 업로드)                     │   │
│  │  - /api/documents   (문서 관리)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Services                                             │   │
│  │  - RAG Service        (개선된 검색 로직)             │   │
│  │  - LlamaParse Service (PDF → Markdown)              │   │
│  │  - Classifier Service (AI 문서 분류)                │   │
│  │  - Embedding Service  (임베딩 생성)                 │   │
│  │  - Supabase Client    (DB 연동)                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
┌──────────────┐ ┌─────────┐ ┌──────────────┐
│   OpenAI     │ │LlamaParse│ │  Supabase    │
│   API        │ │   API    │ │  (PostgreSQL)│
│              │ │          │ │  + pgvector  │
└──────────────┘ └─────────┘ └──────────────┘
```

---

## 🎯 핵심 기능

### 1. 채팅 시스템 (RAG)

#### 흰 박스 (일반 모드)
```
사용자 질문
  ↓
관련 문서 없음
  ↓
GPT 일반 지식 기반 답변
  ↓
흰 박스 표시
```

#### 파란 박스 (RAG 모드)
```
사용자 질문
  ↓
개선된 RAG 검색 (6단계)
  ↓
관련 문서 발견
  ↓
GPT + 문서 기반 답변
  ↓
파란 박스 + 출처 표시
```

### 2. 문서 업로드 파이프라인

```
PDF 업로드 (관리자 페이지)
  ↓
1. LlamaParse OCR (Premium Mode)
   - 한글 완벽 인식
   - 표 구조 보존
   - Markdown 변환
  ↓
2. AI 문서 분류 (GPT-4o-mini)
   - 처음 3000자 읽고 분석
   - 카테고리 자동 판단
   - 신뢰도/이유/키워드 추출
  ↓
3. 텍스트 청킹 (LangChain)
   - Chunk Size: 1200자
   - Overlap: 200자
   - 의미 단위 분리
  ↓
4. 임베딩 생성 (OpenAI)
   - 모델: text-embedding-3-small
   - 차원: 1536
   - 배치 처리 (10개씩)
  ↓
5. Supabase 저장
   - 테이블: policy_documents
   - content: 텍스트
   - embedding: 벡터
   - metadata: JSON (제목, 출처, 카테고리 등)
```

---

## 🔍 RAG 알고리즘 (개선된 버전)

### 단계별 필터링 방식

```python
# 1단계: 문서 메타데이터 조회
모든 문서의 제목, 키워드, 카테고리 조회
  ↓
# 2단계: GPT 문서 필터링
GPT에게 질문과 문서 목록 제공
  → "어떤 문서가 관련 있나요?"
  → GPT가 관련 문서 번호 반환
  ↓
# 3단계: 핵심 키워드 추출
질문에서 중요 단어 추출
  - 문서의 키워드와 매칭
  - 중요 단어들 (2028, 입학, 전형 등)
  ↓
# 4단계: 선택된 문서의 청크만 조회
2단계에서 선택된 문서의 청크만 DB 조회
  → 효율성 향상!
  ↓
# 5단계: 키워드 기반 점수 계산
각 청크마다:
  점수 = 키워드 포함 개수 + (키워드 빈도 × 0.5)
  
예시:
  "입학전형"이 5번 → 1 + (5 × 0.5) = 3.5점
  "개편"이 2번 → 1 + (2 × 0.5) = 2점
  "2028"이 3번 → 1 + (3 × 0.5) = 2.5점
  총점: 8점
  ↓
# 6단계: 상위 3개 청크 반환
점수 순으로 정렬
  → 상위 3개 선택
  → GPT에게 전달
  ↓
# 7단계: GPT 답변 생성
컨텍스트 = 상위 3개 청크
프롬프트 = 질문 + 컨텍스트
  → GPT가 정확한 답변 생성
  → 출처 포함
```

### 기존 벡터 검색과의 차이

| 구분 | 기존 방식 | 개선된 방식 |
|------|-----------|-------------|
| **검색 방법** | 모든 청크 벡터 검색 | GPT 필터링 → 키워드 검색 |
| **효율성** | 느림 (모든 청크 계산) | 빠름 (선택된 문서만) |
| **정확도** | 유사도 0.5대 (낮음) | 키워드 매칭 (명확) |
| **디버깅** | 블랙박스 | 각 단계 로그 출력 |
| **확장성** | 데이터 많으면 느려짐 | 속도 유지 |

---

## 📦 데이터 파이프라인

### PDF 업로드 플로우 (상세)

```
관리자가 PDF 업로드
  ↓
[프론트엔드]
  - FormData 생성 (file, title, source)
  - POST /api/upload/
  - 120초 timeout 설정
  ↓
[백엔드 - 파일 검증]
  - 파일 타입 확인 (PDF만)
  - 파일 크기 확인 (50MB 이하)
  ↓
[LlamaParse Service - OCR]
  임시 파일 저장 (/tmp/xxx.pdf)
    ↓
  LlamaParse API 호출
    - Premium Mode: True
    - Language: Korean
    - Result Type: Markdown
    ↓
  Markdown 변환 완료 (20-30초)
    ↓
  임시 파일 삭제
  ↓
[Classifier Service - AI 분류]
  Markdown 처음 3000자 추출
    ↓
  GPT-4o-mini 호출
    프롬프트: "이 문서를 분류하세요"
    옵션:
      - policy: 정책/요강 문서
      - admission: 입시 결과
      - other: 기타
    ↓
  결과: {
    category: "policy",
    confidence: 0.95,
    reason: "...",
    keywords: ["입학전형", "개편", ...]
  }
  ↓
[Embedding Service - 청킹]
  RecursiveCharacterTextSplitter
    - chunk_size: 1200
    - chunk_overlap: 200
    - separators: ["\n\n", "\n", " "]
    ↓
  청크 생성 (예: 7개)
  ↓
[Embedding Service - 임베딩]
  배치 처리 (10개씩)
    ↓
  각 청크를 OpenAI API로 전송
    - 모델: text-embedding-3-small
    - 출력: 1536차원 벡터
    ↓
  임베딩 리스트 반환
  ↓
[Supabase Service - 저장]
  각 청크마다:
    content: 텍스트
    embedding: "[0.1,0.2,...,0.3]" (문자열로 변환!)
    metadata: {
      title, source, fileName,
      category, confidence, keywords,
      chunkIndex, totalChunks, ...
    }
    ↓
  INSERT INTO policy_documents
  ↓
[응답]
  {
    success: true,
    classification: {...},
    stats: {
      totalPages: 10,
      chunksTotal: 7,
      chunksSuccess: 7,
      processingTime: "34.33초"
    }
  }
```

---

## 📂 프로젝트 구조

```
입시코디ai/
├── backend/                          # FastAPI 백엔드
│   ├── main.py                       # FastAPI 앱 진입점
│   ├── config.py                     # 환경 변수 설정
│   ├── .env                          # API 키 등 (gitignore)
│   ├── requirements.txt              # Python 패키지
│   │
│   ├── routers/                      # API 라우터
│   │   ├── chat.py                   # POST /api/chat
│   │   ├── upload.py                 # POST /api/upload
│   │   └── documents.py              # GET/DELETE /api/documents
│   │
│   ├── services/                     # 비즈니스 로직
│   │   ├── rag_service.py            # 개선된 RAG 검색
│   │   ├── llamaparse_service.py     # PDF → Markdown
│   │   ├── classifier_service.py     # AI 문서 분류
│   │   ├── embedding_service.py      # 임베딩 생성
│   │   └── supabase_client.py        # DB 연동
│   │
│   ├── test_pipeline.py              # 전체 파이프라인 테스트
│   ├── test_improved_rag.py          # RAG 테스트
│   └── venv/                         # Python 가상환경
│
├── frontend/                         # React 프론트엔드
│   ├── package.json                  # npm 패키지
│   ├── vite.config.ts                # Vite 설정 (프록시 포함)
│   ├── tsconfig.json                 # TypeScript 설정
│   ├── tailwind.config.js            # TailwindCSS 설정
│   │
│   ├── src/
│   │   ├── main.tsx                  # React 진입점
│   │   ├── App.tsx                   # 라우팅
│   │   │
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx          # 채팅 페이지
│   │   │   └── AdminPage.tsx         # 관리자 페이지
│   │   │
│   │   ├── components/
│   │   │   └── ChatMessage.tsx       # 메시지 컴포넌트
│   │   │
│   │   └── api/
│   │       └── client.ts             # API 클라이언트 (Axios)
│   │
│   └── node_modules/
│
├── 문서/                              # 프로젝트 문서
│   ├── PROJECT-DOCUMENTATION.md      # 이 파일!
│   ├── VECTOR-SEARCH-EXPLAINED.md    # 벡터 검색 원리
│   ├── IMPROVED-RAG-COMPLETE.md      # 개선된 RAG 설명
│   ├── RAG-FIXED.md                  # RAG 수정 내역
│   ├── FINAL-WORKING.md              # 최종 작동 확인
│   └── TEST-SUCCESS.md               # 테스트 성공 보고서
│
├── 업로드 파일/                       # 업로드된 PDF
│   ├── 2028학년도 대학입학전형기본사항.pdf
│   └── 2028 대입 정보 제공 설명회_2.pdf
│
├── setup.sh                          # 자동 설치 스크립트
├── start.sh                          # 자동 실행 스크립트
├── README.md                         # 프로젝트 README
└── .gitignore                        # Git 무시 파일
```

---

## 🔌 API 명세

### 1. 채팅 API

**POST** `/api/chat/`

**Request:**
```json
{
  "message": "2028학년도 서울대 입학전형 개편 사항"
}
```

**Response (RAG 모드):**
```json
{
  "response": "2028학년도 서울대학교 입학전형에 대한 주요 사항은...",
  "isFactMode": true,
  "source": "대입정보포털"
}
```

**Response (일반 모드):**
```json
{
  "response": "안녕하세요! 입시에 대해 설명드리겠습니다...",
  "isFactMode": false,
  "source": ""
}
```

### 2. 업로드 API

**POST** `/api/upload/`

**Request (multipart/form-data):**
```
file: [PDF 파일]
title: "2028학년도 대입정보"
source: "대입정보포털"
```

**Response:**
```json
{
  "success": true,
  "message": "파일이 성공적으로 처리되었습니다.",
  "classification": {
    "category": "policy",
    "categoryName": "정책/요강 문서",
    "emoji": "📋",
    "confidence": 0.95,
    "reason": "문서 내용이 2028학년도 서울대학교 입학전형...",
    "keywords": ["입학전형", "개편", "평가체제", ...]
  },
  "stats": {
    "totalPages": 10,
    "chunksTotal": 7,
    "chunksSuccess": 7,
    "chunksFailed": 0,
    "processingTime": "34.33초",
    "markdownSize": "6.77KB"
  },
  "preview": {
    "firstChunk": "# 2028학년도 전형 운영 계획 안내..."
  }
}
```

### 3. 문서 목록 API

**GET** `/api/documents`

**Response:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "title": "2028학년도 대입정보",
      "source": "대입정보포털",
      "fileName": "2028_대입_정보.pdf",
      "category": "정책/요강 문서",
      "uploadedAt": "2026-01-13T13:21:58+00:00"
    }
  ]
}
```

### 4. 문서 삭제 API

**DELETE** `/api/documents/{id}`

**Response:**
```json
{
  "success": true
}
```

---

## 🗄 데이터베이스 스키마

### Supabase PostgreSQL + pgvector

```sql
-- 1. 벡터 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 정책/요강 문서 테이블 (RAG용)
CREATE TABLE policy_documents (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  content TEXT NOT NULL,                    -- 청크 텍스트
  metadata JSONB,                           -- 메타데이터
  embedding VECTOR(1536),                   -- 임베딩 벡터
  created_at TIMESTAMP WITH TIME ZONE 
    DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- metadata 구조:
{
  "title": "문서 제목",
  "source": "출처",
  "fileName": "파일명.pdf",
  "category": "policy",
  "categoryName": "정책/요강 문서",
  "emoji": "📋",
  "confidence": 0.95,
  "reason": "분류 이유",
  "keywords": ["키워드1", "키워드2", ...],
  "totalPages": 10,
  "parseMethod": "llamaparse",
  "chunkIndex": 0,
  "totalChunks": 7
}

-- 3. 벡터 검색 함수
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.78,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    policy_documents.id,
    policy_documents.content,
    policy_documents.metadata,
    1 - (policy_documents.embedding <=> query_embedding) AS similarity
  FROM policy_documents
  WHERE 1 - (policy_documents.embedding <=> query_embedding) > match_threshold
  ORDER BY policy_documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 4. 채팅 로그 테이블
CREATE TABLE chat_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users,
  message TEXT NOT NULL,
  response TEXT NOT NULL,
  is_fact_mode BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE 
    DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. 대학 정보 테이블
CREATE TABLE universities (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  region TEXT,
  logo_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE 
    DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. 입시 결과 테이블
CREATE TABLE admission_stats (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  univ_id UUID REFERENCES universities(id) NOT NULL,
  department TEXT NOT NULL,
  track TEXT,
  year INT NOT NULL,
  recruit_count INT,
  competition_rate FLOAT,
  cut_70 FLOAT,
  created_at TIMESTAMP WITH TIME ZONE 
    DEFAULT timezone('utc'::text, now()) NOT NULL
);
```

---

## 🚀 실행 방법

### 1. 환경 설정

#### 필수 API 키
```bash
# OpenAI API Key
https://platform.openai.com/api-keys

# LlamaParse API Key
https://cloud.llamaindex.ai/api-key

# Supabase
https://supabase.com/dashboard
```

#### backend/.env 파일 생성
```env
SUPABASE_URL=https://rnitmphvahpkosvxjshw.supabase.co
SUPABASE_KEY=sb_secret_K2ZLZ...  # Secret key!
OPENAI_API_KEY=sk-proj-7QeI9...
LLAMA_API_KEY=llx-...
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
```

### 2. 자동 설치 (권장)

```bash
cd "/Users/rlaxogns100/Desktop/Projects/입시코디ai"
./setup.sh
```

이 스크립트가 자동으로:
- Python venv 생성
- backend/requirements.txt 설치
- frontend/package.json 설치

### 3. 자동 실행 (권장)

```bash
./start.sh
```

이 스크립트가 자동으로:
- 백엔드 시작 (포트 8000)
- 프론트엔드 시작 (포트 5173)

### 4. 수동 실행

#### 터미널 1 - 백엔드
```bash
cd backend
source venv/bin/activate
python main.py
```

#### 터미널 2 - 프론트엔드
```bash
cd frontend
npm run dev
```

### 5. 접속

```
프론트엔드: http://localhost:5173
백엔드 API: http://localhost:8000
API 문서:   http://localhost:8000/docs
```

---

## 🧪 테스트

### 로컬 파이프라인 테스트
```bash
cd backend
source venv/bin/activate
python test_pipeline.py
```

### RAG 시스템 테스트
```bash
cd backend
source venv/bin/activate
python test_improved_rag.py
```

### API 테스트 (curl)
```bash
# 헬스체크
curl http://localhost:8000/api/health

# 채팅
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "2028학년도 서울대 입학전형"}'

# 업로드
curl -X POST http://localhost:8000/api/upload/ \
  -F "file=@파일명.pdf" \
  -F "title=제목" \
  -F "source=출처"
```

---

## 📊 성능 지표

### 처리 시간
```
- PDF 업로드 (2.5MB): 30-40초
  - LlamaParse OCR: 20-30초
  - AI 분류: 3-5초
  - 청킹: 1초
  - 임베딩: 3-5초
  - DB 저장: 1-2초

- 채팅 응답: 5-20초
  - RAG 검색: 2-3초
  - GPT 답변 생성: 3-15초
```

### 데이터 크기
```
- 임베딩 차원: 1536
- 청크 크기: 800-1400자
- Overlap: 200자
- 청크당 임베딩 크기: ~24KB (JSON)
```

---

## 🔐 보안

### API 키 관리
```
- .env 파일 사용
- .gitignore에 .env 추가
- Secret key 사용 (Supabase)
```

### CORS 설정
```python
# backend/main.py
allow_origins=[
    "http://localhost:5173",
    "http://localhost:3000",
]
```

### 파일 검증
```python
# 파일 타입 검증
if file.content_type != "application/pdf":
    raise HTTPException(400, "PDF만 가능")

# 파일 크기 검증
MAX_SIZE = 50 * 1024 * 1024  # 50MB
if len(file_bytes) > MAX_SIZE:
    raise HTTPException(400, "50MB 이하만 가능")
```

---

## 🐛 트러블슈팅

### 백엔드 포트 충돌
```bash
lsof -ti:8000 | xargs kill -9
```

### 프론트엔드 CORS 에러
```typescript
// frontend/vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

### Supabase 연결 오류
```
- Secret key 사용 확인
- SUPABASE_URL 확인
- 벡터 검색 함수 생성 확인
```

### 임베딩 형식 오류
```python
# 문자열로 변환 필수!
embedding_str = '[' + ','.join(map(str, embedding)) + ']'
```

---

## 📈 향후 개선 사항

### 1. 성능 최적화
- [ ] 임베딩 캐싱
- [ ] 청크 인덱싱
- [ ] 배치 처리 최적화

### 2. 기능 추가
- [ ] 사용자 인증
- [ ] 대화 히스토리
- [ ] 문서 버전 관리
- [ ] 다중 파일 업로드

### 3. UI/UX 개선
- [ ] 실시간 처리 상태 표시
- [ ] 마크다운 렌더링
- [ ] 다크 모드

### 4. 데이터 확장
- [ ] 더 많은 대학 정보
- [ ] 입시 결과 데이터
- [ ] 과거 년도 자료

---

## 🎓 학습 리소스

### 벡터 검색
- `VECTOR-SEARCH-EXPLAINED.md` 참고

### RAG 시스템
- `IMPROVED-RAG-COMPLETE.md` 참고

### 프로젝트 히스토리
- `FINAL-WORKING.md`
- `TEST-SUCCESS.md`
- `RAG-FIXED.md`

---

## 📞 지원

### 문제 발생 시
1. 백엔드 로그 확인: `/tmp/backend_*.log`
2. 브라우저 콘솔 확인
3. API 문서 확인: `http://localhost:8000/docs`

### 문서
- README.md
- 이 문서 (PROJECT-DOCUMENTATION.md)

---

## 📝 변경 이력

### v2.0.0 (2026-01-13)
- FastAPI + React 분리 아키텍처
- 개선된 RAG 시스템 (단계별 필터링)
- LlamaParse Premium Mode
- 키워드 기반 검색

### v1.0.0 (2026-01-13)
- Next.js 기반 MVP
- 기본 RAG 구현
- 벡터 검색

---

**프로젝트 완성! 🎉**

모든 기능이 정상 작동합니다.

