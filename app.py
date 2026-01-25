import streamlit as st
from langchain_core.messages.chat import ChatMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_teddynote.prompts import load_prompt
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_teddynote import logging
from dotenv import load_dotenv
import os

# API KEY 정보로드
load_dotenv()

# GEMINI_API_KEY를 GOOGLE_API_KEY로 매핑
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 프로젝트 이름을 입력합니다.
logging.langsmith("[Project] PDF RAG - Gemini")

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 파일 업로드 전용 폴더
if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

st.title("🎓 대학 입시 컨설턴트 (Gemini)")

# 처음 1번만 실행하기 위한 코드
if "messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages"] = []

if "chain" not in st.session_state:
    # 아무런 파일을 업로드 하지 않을 경우
    st.session_state["chain"] = None

# 사이드바 생성
with st.sidebar:
    # 초기화 버튼 생성
    clear_btn = st.button("대화 초기화")
    
    # 파일 업로드
    uploaded_file = st.file_uploader("PDF 파일 업로드", type=["pdf"])
    
    # 모델 고정
    selected_model = "gemini-2.0-flash-lite"
    
    st.markdown("---")
    st.markdown("### 📌 사용 방법")
    st.markdown("1. 대학 입시 모집요강 PDF 업로드")
    st.markdown("2. 전형, 학과, 일정 등 질문")
    st.markdown("3. AI 입시 전문가가 답변")
    st.markdown("")
    st.markdown("✅ 모든 대학 지원 가능")
    
    st.markdown("---")
    st.markdown("### ⚙️ 고성능 설정")
    st.markdown(f"**모델**: {selected_model}")
    st.markdown(f"**Temperature**: 0 (최고 정확도)")
    st.markdown(f"**검색 방식**: MMR Advanced")
    st.markdown(f"**검색 결과**: 20개 (최대)")
    st.markdown(f"**후보 문서 풀**: 50개")
    st.markdown(f"**청크 크기**: 3000자 (극대화)")
    st.markdown(f"**청크 중복**: 600자 (정보 손실 방지)")
    if uploaded_file:
        st.markdown(f"**파일**: {uploaded_file.name}")
        st.markdown("⚠️ 정확도 최우선 모드")

# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages"]:
        st.chat_message(chat_message.role).write(chat_message.content)

# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages"].append(ChatMessage(role=role, content=message))

# 파일을 캐시 저장(시간이 오래 걸리는 작업을 처리할 예정)
@st.cache_resource(show_spinner="업로드한 파일을 처리 중입니다...")
def embed_file(file):
    # 업로드한 파일을 캐시 디렉토리에 저장합니다.
    file_content = file.read()
    file_path = f"./.cache/files/{file.name}"
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 단계 1: 문서 로드(Load Documents)
    loader = PDFPlumberLoader(file_path)
    docs = loader.load()
    
    # 단계 2: 문서 분할(Split Documents)
    # 최대 정확도를 위한 대용량 청크 설정 (업로드 시간보다 정확도 우선)
    # chunk_size: 매우 크게 설정하여 완전한 문맥과 표 전체 보존
    # chunk_overlap: 매우 크게 설정하여 정보 손실 최소화
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,  # 최대 문맥 보존
        chunk_overlap=600,  # 정보 손실 방지
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    split_documents = text_splitter.split_documents(docs)
    
    # 단계 3: 임베딩(Embedding) 생성 - Google Gemini Embeddings 사용
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # 단계 4: DB 생성(Create DB) 및 저장
    # 벡터스토어를 생성합니다.
    vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)
    
    # 단계 5: 검색기(Retriever) 생성
    # 최대 정확도를 위한 대규모 검색 설정 (성능 최우선)
    # search_type="mmr": 최대 한계 관련성 (다양성과 관련성의 균형)
    # k=20: 매우 많은 관련 청크를 검색하여 정보 누락 방지
    # fetch_k=50: 초기 후보를 50개로 대폭 증가
    # lambda_mult=0.8: 관련성을 최대한 우선시 (정확도 극대화)
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 20,
            "fetch_k": 50,
            "lambda_mult": 0.8
        }
    )
    
    return retriever

# 체인 생성
def create_chain(retriever, model_name="gemini-2.0-flash-lite"):
    # 단계 6: 프롬프트 생성(Create Prompt)
    # 프롬프트를 생성합니다.
    prompt = load_prompt("prompts/pdf-rag.yaml", encoding="utf-8")
    
    # 단계 7: 언어모델(LLM) 생성 - Google Gemini 사용
    # 모델(LLM) 을 생성합니다.
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    
    # 단계 8: 체인(Chain) 생성
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

# 파일이 업로드 되었을 때
if uploaded_file:
    # 파일 업로드 후 retriever 생성 (작업시간이 오래 걸릴 예정...)
    retriever = embed_file(uploaded_file)
    chain = create_chain(retriever, model_name=selected_model)
    st.session_state["chain"] = chain

# 초기화 버튼이 눌리면...
if clear_btn:
    st.session_state["messages"] = []

# 이전 대화 기록 출력
print_messages()

# 사용자의 입력
user_input = st.chat_input("입시 관련 질문을 해주세요! (예: 네오르네상스 전형 지원 자격은?)")

# 경고 메시지를 띄우기 위한 빈 영역
warning_msg = st.empty()

# 만약에 사용자 입력이 들어오면...
if user_input:
    # chain 을 생성
    chain = st.session_state["chain"]
    
    if chain is not None:
        # 사용자의 입력
        st.chat_message("user").write(user_input)
        
        # 스트리밍 호출
        response = chain.stream(user_input)
        with st.chat_message("assistant"):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()
            ai_answer = ""
            for token in response:
                ai_answer += token
                container.markdown(ai_answer)
        
        # 대화기록을 저장한다.
        add_message("user", user_input)
        add_message("assistant", ai_answer)
    else:
        # 파일을 업로드 하라는 경고 메시지 출력
        warning_msg.error("대학 입시 모집요강 PDF를 먼저 업로드 해주세요.")

