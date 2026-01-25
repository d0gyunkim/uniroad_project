import streamlit as st
from langchain_core.messages.chat import ChatMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_teddynote.prompts import load_prompt
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_teddynote import logging
from dotenv import load_dotenv
import os

# Multi-modal을 위한 추가 import
from unstructured.partition.pdf import partition_pdf
from langchain.text_splitter import CharacterTextSplitter

# API KEY 정보로드
load_dotenv()

# GEMINI_API_KEY를 GOOGLE_API_KEY로 매핑
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 프로젝트 이름을 입력합니다.
logging.langsmith("[Project] PDF RAG - Gemini - MultiModal")

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 파일 업로드 전용 폴더
if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

st.title("🎓 대학 입시 컨설턴트 (Multi-Modal)")

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
    st.markdown("### ⚙️ Multi-Modal 설정")
    st.markdown(f"**모델**: {selected_model}")
    st.markdown(f"**Temperature**: 0")
    st.markdown(f"**표 별도 처리**: ✅")
    st.markdown(f"**검색 결과**: 20개")
    st.markdown(f"**청크 전략**: 의미 단위")
    if uploaded_file:
        st.markdown(f"**파일**: {uploaded_file.name}")
        st.markdown("🔥 **Multi-Modal 모드**")

# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages"]:
        st.chat_message(chat_message.role).write(chat_message.content)

# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages"].append(ChatMessage(role=role, content=message))

# Multi-modal PDF 처리 함수
def extract_pdf_elements_multimodal(file_path):
    """
    Unstructured를 사용하여 PDF에서 표와 텍스트를 분리 추출
    """
    raw_elements = partition_pdf(
        file_path,
        extract_images_in_pdf=False,  # 이미지는 제외 (속도 향상)
        infer_table_structure=True,   # 표 구조 인식
        chunking_strategy="by_title",  # 제목별로 청킹
        max_characters=4000,
        new_after_n_chars=3800,
        combine_text_under_n_chars=2000,
    )
    
    return raw_elements

def categorize_elements(raw_pdf_elements):
    """
    추출된 요소를 표와 텍스트로 분류
    """
    tables = []
    texts = []
    
    for element in raw_pdf_elements:
        element_type = str(type(element))
        
        if "Table" in element_type:
            tables.append(str(element))
        elif "CompositeElement" in element_type or "Text" in element_type:
            texts.append(str(element))
    
    return texts, tables

def generate_table_summaries(tables):
    """
    표를 LLM으로 요약하여 검색 최적화
    """
    if not tables:
        return []
    
    prompt_text = """당신은 대학 입시 모집요강의 표를 분석하는 전문가입니다.
    
아래 표의 내용을 상세하게 요약하세요. 
대학명, 전형명, 학과명, 모집 인원, 지원 자격, 반영비율 등 표에 포함된 모든 정보를 빠짐없이 포함하세요.

표: {element}

요약:"""
    
    from langchain_core.prompts import ChatPromptTemplate
    
    prompt = ChatPromptTemplate.from_template(prompt_text)
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0)
    summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()
    
    # 배치로 처리
    table_summaries = summarize_chain.batch(tables, {"max_concurrency": 3})
    
    return table_summaries

# 파일을 캐시 저장(시간이 오래 걸리는 작업을 처리할 예정)
@st.cache_resource(show_spinner="Multi-Modal 방식으로 파일을 처리 중입니다... (표 별도 분석)")
def embed_file_multimodal(file):
    # 업로드한 파일을 캐시 디렉토리에 저장합니다.
    file_content = file.read()
    file_path = f"./.cache/files/{file.name}"
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 단계 1: Multi-modal 문서 로드 (표와 텍스트 분리)
    st.info("📄 단계 1/4: PDF 파싱 중... (표 구조 인식)")
    raw_elements = extract_pdf_elements_multimodal(file_path)
    
    # 단계 2: 표와 텍스트 분류
    st.info("🔍 단계 2/4: 표와 텍스트 분류 중...")
    texts, tables = categorize_elements(raw_elements)
    
    st.success(f"✅ 텍스트 {len(texts)}개, 표 {len(tables)}개 추출 완료!")
    
    # 단계 3: 표 요약 생성 (검색 최적화)
    st.info("📊 단계 3/4: 표 요약 생성 중... (AI 분석)")
    table_summaries = generate_table_summaries(tables)
    
    # 텍스트와 표 요약을 결합
    all_texts = texts + table_summaries
    
    # 단계 4: 임베딩 생성
    st.info("🧠 단계 4/4: 임베딩 생성 중...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # 벡터스토어 생성 (텍스트 + 표 요약)
    from langchain.docstore.document import Document
    documents = [Document(page_content=text) for text in all_texts]
    
    vectorstore = FAISS.from_documents(documents=documents, embedding=embeddings)
    
    # 단계 5: 검색기 생성
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 20,
            "fetch_k": 50,
            "lambda_mult": 0.8
        }
    )
    
    st.success("✅ Multi-Modal 처리 완료!")
    
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
    retriever = embed_file_multimodal(uploaded_file)
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

