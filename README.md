# 🎓 유니로드

대학 입시 상담 AI 챗봇 - FastAPI + React

## ✨ 주요 기능

### 1. 💬 AI 채팅
- **일반 모드**: GPT 기반 일반 상담 (흰 박스)
- **RAG 모드**: 업로드된 문서 기반 정확한 정보 제공 (파란 박스 + 출처 표시)

### 2. 📚 문서 관리
- PDF 업로드 (드래그 앤 드롭 지원)
- LlamaParse로 자동 변환 (표 구조 보존)
- GPT 기반 자동 분류 (정책/통계/대학정보)
- 벡터 임베딩 & 검색

### 3. 🤖 자동화
- PDF → Markdown 변환
- 문서 자동 분류
- 텍스트 청킹
- 임베딩 생성
- Supabase 자동 저장

---

## 🏗️ 기술 스택

### 백엔드
- **FastAPI** - Python 웹 프레임워크
- **LlamaParse** - PDF 파싱 (표 보존)
- **OpenAI** - GPT-4o-mini, text-embedding-3-small
- **Supabase** - PostgreSQL + pgvector
- **LangChain** - 텍스트 청킹

### 프론트엔드
- **React 18** - UI 라이브러리
- **Vite** - 빌드 도구
- **TypeScript** - 타입 안정성
- **TailwindCSS** - 스타일링
- **Axios** - HTTP 클라이언트

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd 입시코디ai

# 자동 설치 (권장)
chmod +x setup.sh
./setup.sh
```

### 2. 환경 설정

`backend/.env` 파일을 열어서 API 키 입력:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
LLAMA_API_KEY=your_llama_key
```

### 3. 실행

```bash
# 자동 실행 (macOS)
chmod +x start.sh
./start.sh

# 또는 수동 실행
# 터미널 1 - 백엔드
cd backend
source venv/bin/activate
python main.py

# 터미널 2 - 프론트엔드
cd frontend
npm run dev
```

### 4. 접속

- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

---

## 📁 프로젝트 구조

```
입시코디ai/
├── backend/                # FastAPI 백엔드
│   ├── main.py            # 앱 진입점
│   ├── config.py          # 환경 설정
│   ├── routers/           # API 라우터
│   │   ├── chat.py       # 채팅 API
│   │   ├── upload.py     # 업로드 API
│   │   └── documents.py  # 문서 관리 API
│   ├── services/          # 비즈니스 로직
│   │   ├── llamaparse_service.py      # PDF 파싱
│   │   ├── classifier_service.py      # 문서 분류
│   │   ├── embedding_service.py       # 임베딩 생성
│   │   └── supabase_client.py         # DB 연결
│   └── requirements.txt   # Python 패키지
│
├── frontend/              # React 프론트엔드
│   ├── src/
│   │   ├── pages/        # 페이지
│   │   │   ├── ChatPage.tsx      # 채팅 페이지
│   │   │   └── AdminPage.tsx     # 관리자 페이지
│   │   ├── components/   # UI 컴포넌트
│   │   ├── api/          # API 클라이언트
│   │   └── App.tsx       # 앱 루트
│   └── package.json       # npm 패키지
│
├── setup.sh               # 자동 설치 스크립트
├── start.sh               # 자동 실행 스크립트
└── README.md              # 이 파일
```

---

## 🔧 개발 가이드

### 백엔드 개발

```bash
cd backend
source venv/bin/activate

# 개발 서버 (자동 리로드)
uvicorn main:app --reload --port 8000

# 테스트
pytest

# 타입 체크
mypy .
```

### 프론트엔드 개발

```bash
cd frontend

# 개발 서버
npm run dev

# 빌드
npm run build

# 프리뷰
npm run preview
```

---

## 📊 API 엔드포인트

### 채팅
- `POST /api/chat` - 메시지 전송

### 업로드
- `POST /api/upload` - PDF 업로드

### 문서 관리
- `GET /api/documents` - 문서 목록
- `DELETE /api/documents/{id}` - 문서 삭제

상세 문서: http://localhost:8000/docs

---

## 🐳 Docker 배포 (선택)

```bash
# Docker Compose로 실행
docker-compose up -d

# 중지
docker-compose down
```

---

## 🌐 AWS 서버 배포

### 1. 서버 접속

```bash
ssh ubuntu@your-server-ip
```

### 2. 코드 업로드

```bash
git clone <repository-url>
cd 입시코디ai
./setup.sh
```

### 3. Nginx 설정

```nginx
server {
    listen 80;
    
    # 프론트엔드
    location / {
        root /var/www/html;
        try_files $uri /index.html;
    }
    
    # 백엔드 API
    location /api/ {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. 서비스 등록

```bash
# systemd 서비스 생성
sudo nano /etc/systemd/system/입시코디-backend.service

# 서비스 시작
sudo systemctl start 입시코디-backend
sudo systemctl enable 입시코디-backend
```

---

## 🤝 기여

이슈 및 PR 환영합니다!

---

## 📝 라이선스

MIT License

---

## 📧 문의

질문이 있으시면 이슈를 등록해주세요.
