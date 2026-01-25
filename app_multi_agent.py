import streamlit as st
from langchain_core.messages.chat import ChatMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_teddynote.prompts import load_prompt
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnablePassthrough
from langchain_teddynote import logging
from dotenv import load_dotenv
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# API KEY 정보로드
load_dotenv()

# GEMINI_API_KEY를 GOOGLE_API_KEY로 매핑
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 프로젝트 이름을 입력합니다.
logging.langsmith("[Project] Multi-Agent RAG - Gemini")

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

if not os.path.exists(".cache/multi_agent"):
    os.mkdir(".cache/multi_agent")

st.title("🤖 멀티 에이전트 입시 컨설턴트")

# 처음 1번만 실행하기 위한 코드
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "agents" not in st.session_state:
    st.session_state["agents"] = None

if "coordinator" not in st.session_state:
    st.session_state["coordinator"] = None

# 사이드바 생성
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    
    # 분할 PDF 폴더 경로
    pdf_folder = st.text_input(
        "분할 PDF 폴더 경로",
        value="경희대_수시요강_분할표"
    )
    
    load_btn = st.button("PDF 로드 및 에이전트 생성")
    
    selected_model = "gemini-2.0-flash-lite"
    
    # 재시도 설정
    max_retries = st.slider("최대 재시도 횟수", min_value=1, max_value=5, value=3, help="답변 품질이 부족할 때 재시도하는 최대 횟수")
    
    st.markdown("---")
    st.markdown("### 🤖 멀티 에이전트 시스템")
    st.markdown("1. 4개 PDF를 각각 처리")
    st.markdown("2. 각 에이전트가 **문서 기반** 독립 답변")
    st.markdown("3. 코디네이터가 자연스럽게 통합")
    st.markdown("4. **품질 평가 및 자동 재시도**")
    st.markdown("")
    st.markdown("✅ 정보: 문서 기반 엄격")
    st.markdown("✅ 답변: 자연스럽고 친절")
    st.markdown("✅ 품질: 자동 평가 및 재시도")
    
    st.markdown("---")
    st.markdown("### ⚙️ 시스템 상태")
    if st.session_state["agents"]:
        st.success(f"✅ {len(st.session_state['agents'])}개 에이전트 활성화")
        st.info("📄 문서 기반 엄격 모드")
    else:
        st.warning("⏳ 에이전트 대기 중")

# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages"]:
        st.chat_message(chat_message.role).write(chat_message.content)

# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages"].append(ChatMessage(role=role, content=message))

# 단일 PDF를 임베딩하는 함수
def embed_single_pdf(pdf_path, pdf_name):
    """
    단일 PDF를 임베딩하여 retriever 반환
    """
    # 문서 로드
    loader = PDFPlumberLoader(pdf_path)
    docs = loader.load()
    
    # 문서 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=600,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    split_documents = text_splitter.split_documents(docs)
    
    # 임베딩 생성
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # 벡터스토어 생성
    vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)
    
    # 검색기 생성
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 15,  # 멀티 에이전트이므로 개별 에이전트는 조금 줄임
            "fetch_k": 30,
            "lambda_mult": 0.8
        }
    )
    
    return {
        "name": pdf_name,
        "retriever": retriever,
        "path": pdf_path
    }

# 멀티 에이전트 로드
@st.cache_resource(show_spinner="멀티 에이전트 시스템 초기화 중...")
def load_multi_agents(folder_path):
    """
    폴더 내 모든 PDF를 로드하여 멀티 에이전트 생성
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        st.error(f"폴더를 찾을 수 없습니다: {folder_path}")
        return None
    
    # PDF 파일 찾기
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        st.error(f"폴더에 PDF 파일이 없습니다: {folder_path}")
        return None
    
    st.info(f"📄 {len(pdf_files)}개의 PDF 파일 발견")
    
    agents = []
    
    # 각 PDF에 대해 에이전트 생성
    for idx, pdf_file in enumerate(pdf_files, 1):
        with st.spinner(f"에이전트 {idx}/{len(pdf_files)} 생성 중... ({pdf_file.name})"):
            agent = embed_single_pdf(str(pdf_file), pdf_file.stem)
            agents.append(agent)
            st.success(f"✅ 에이전트 {idx} 준비 완료: {pdf_file.name}")
    
    return agents

# 단일 에이전트 체인 생성
def create_agent_chain(retriever, model_name="gemini-2.0-flash-lite"):
    """
    단일 에이전트의 RAG 체인 생성 - 문서 기반 엄격 모드
    """
    # 에이전트 전용 프롬프트 사용 (문서 기반 엄격)
    prompt = load_prompt("prompts/pdf-rag-agent.yaml", encoding="utf-8")
    
    # Temperature 0으로 고정 (정확도 최우선)
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

# 코디네이터 생성
def create_coordinator(model_name="gemini-2.0-flash-lite"):
    """
    여러 에이전트의 답변을 평가하고 최적 답변을 선택/종합하는 코디네이터
    """
    coordinator_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 전문 컨설턴트이며, 멀티 에이전트 시스템의 코디네이터입니다.

여러 에이전트가 각자의 문서를 기반으로 같은 질문에 답변했습니다.
당신의 역할은 이 답변들을 통합하여 학생에게 최적의 답변을 제공하는 것입니다.

**정보 출처 규칙 (엄격):**

1. 오직 에이전트들이 문서에서 찾은 구체적인 정보만 사용하세요
2. 에이전트가 "찾을 수 없다"고 한 정보는 추측하거나 만들지 마세요
3. 외부 지식으로 구체적인 수치나 정보를 보충하지 마세요
4. 숫자, 날짜, 인원, 전형명 등 모든 구체적 정보는 에이전트 답변에 있는 것만 사용

**답변 구성 (자연스럽게):**

1. 학생과 학부모가 이해하기 쉽게 명확하고 친절하게 답변하세요
2. 여러 에이전트의 정보를 논리적으로 통합하고 체계적으로 정리하세요
3. 질문의 맥락에 맞게 자연스러운 흐름으로 작성하세요
4. 중복되는 정보는 한 번만 언급하세요
5. 필요시 정보를 정리하여 표나 목록 형태로 제시하세요
6. 모든 에이전트가 정보를 찾지 못했다면, "업로드된 문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요

**중요:**
- 정보(숫자, 날짜, 이름 등) = 에이전트 답변에서만 (엄격)
- 설명 방식 = 자연스럽고 이해하기 쉽게

---

**학생 질문:**
{question}

---

**에이전트 답변들:**

{agent_responses}

---

**최종 답변:**
""")
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    
    chain = coordinator_prompt | llm | StrOutputParser()
    
    return chain

# 답변 품질 평가 함수
def evaluate_answer_quality(question, answer, model_name="gemini-2.0-flash-lite"):
    """
    답변의 품질을 평가하여 적절한지 판단
    """
    evaluation_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 컨설턴트의 답변 품질을 평가하는 전문가입니다.

**평가 기준:**
1. **관련성** (0-10점): 답변이 질문과 직접적으로 관련이 있는가?
2. **완전성** (0-10점): 질문에 대한 답변이 충분히 완전한가? (중요 정보 누락 없음)
3. **정확성** (0-10점): 답변에 구체적인 정보(숫자, 날짜, 이름 등)가 포함되어 있는가?
4. **유용성** (0-10점): 학생/학부모에게 실제로 도움이 되는 답변인가?

**불합격 기준 (다음 중 하나라도 해당되면 불합격):**
- "찾을 수 없습니다", "정보가 없습니다" 같은 불완전한 답변
- 질문과 관련 없는 답변
- 구체적인 정보 없이 추상적인 설명만 있는 답변
- 총점이 30점 미만인 경우

**평가 형식:**
총점: [0-40점]
판정: [합격/불합격]
이유: [간단한 평가 이유]

---
**질문:**
{question}

**답변:**
{answer}

---
**평가:**
""")
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    chain = evaluation_prompt | llm | StrOutputParser()
    
    evaluation = chain.invoke({
        "question": question,
        "answer": answer
    })
    
    # 평가 결과 파싱
    is_acceptable = "불합격" not in evaluation and "합격" in evaluation
    
    return {
        "is_acceptable": is_acceptable,
        "evaluation_text": evaluation
    }

# 멀티 에이전트 질의응답 (재시도 로직 포함)
def multi_agent_query_with_retry(question, agents, coordinator, model_name="gemini-2.0-flash-lite", max_retries=3):
    """
    멀티 에이전트 시스템으로 질문에 답변 (품질 평가 및 재시도 포함)
    """
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            st.warning(f"🔄 {attempt}번째 시도 중... (이전 답변 품질 개선 필요)")
        
        # 단계 1: 각 에이전트에게 질문
        st.info(f"🤖 {len(agents)}개 에이전트에게 질문 중... (시도 {attempt}/{max_retries})")
        
        agent_responses = []
        
        # 병렬 처리로 속도 향상
        def query_agent(agent):
            chain = create_agent_chain(agent["retriever"], model_name)
            response = chain.invoke(question)
            return {
                "agent_name": agent["name"],
                "response": response
            }
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(query_agent, agent) for agent in agents]
            
            for idx, future in enumerate(as_completed(futures), 1):
                result = future.result()
                agent_responses.append(result)
                st.success(f"✅ 에이전트 {idx}/{len(agents)} 답변 완료: {result['agent_name']}")
        
        # 단계 2: 에이전트 답변 표시 (펼침 가능)
        with st.expander(f"🔍 각 에이전트 답변 보기 (시도 {attempt})"):
            for idx, response in enumerate(agent_responses, 1):
                st.markdown(f"**[에이전트 {idx}: {response['agent_name']}]**")
                st.markdown(response['response'])
                st.markdown("---")
        
        # 단계 3: 코디네이터가 최적 답변 선택/종합
        st.info("🎯 코디네이터가 최적 답변 생성 중...")
        
        # 에이전트 답변들을 포맷팅
        formatted_responses = "\n\n".join([
            f"[에이전트 {idx}: {resp['agent_name']}]\n{resp['response']}"
            for idx, resp in enumerate(agent_responses, 1)
        ])
        
        # 코디네이터가 최종 답변 생성
        final_response = coordinator.invoke({
            "question": question,
            "agent_responses": formatted_responses
        })
        
        # 단계 4: 답변 품질 평가
        st.info("📊 답변 품질 평가 중...")
        quality_result = evaluate_answer_quality(question, final_response, model_name)
        
        # 평가 결과 표시
        with st.expander("📋 품질 평가 결과"):
            st.markdown(quality_result["evaluation_text"])
        
        # 품질이 적절하면 반환
        if quality_result["is_acceptable"]:
            if attempt > 1:
                st.success(f"✅ {attempt}번째 시도에서 적절한 답변을 생성했습니다!")
            return final_response
        else:
            if attempt < max_retries:
                st.warning(f"⚠️ 답변 품질이 부족합니다. 재시도합니다... ({attempt}/{max_retries})")
                # 재시도를 위해 더 많은 컨텍스트를 가져오도록 조정
                # (다음 시도에서 더 많은 문서를 검색하도록)
            else:
                st.warning(f"⚠️ 최대 재시도 횟수({max_retries})에 도달했습니다. 현재 답변을 반환합니다.")
                return final_response
    
    # 모든 시도 실패 시 마지막 답변 반환
    return final_response

# 멀티 에이전트 질의응답 (기존 함수 - 호환성 유지)
def multi_agent_query(question, agents, coordinator, model_name="gemini-2.0-flash-lite"):
    """
    멀티 에이전트 시스템으로 질문에 답변 (재시도 로직 포함)
    """
    return multi_agent_query_with_retry(question, agents, coordinator, model_name, max_retries=3)

# PDF 로드 버튼이 눌리면
if load_btn:
    agents = load_multi_agents(pdf_folder)
    if agents:
        st.session_state["agents"] = agents
        st.session_state["coordinator"] = create_coordinator(selected_model)
        st.success(f"🎉 멀티 에이전트 시스템 준비 완료! ({len(agents)}개 에이전트)")
        st.rerun()

# 초기화 버튼이 눌리면
if clear_btn:
    st.session_state["messages"] = []

# 이전 대화 기록 출력
print_messages()

# 사용자의 입력
user_input = st.chat_input("입시 관련 질문을 해주세요!")

# 경고 메시지를 띄우기 위한 빈 영역
warning_msg = st.empty()

# 만약에 사용자 입력이 들어오면...
if user_input:
    agents = st.session_state["agents"]
    coordinator = st.session_state["coordinator"]
    
    if agents and coordinator:
        # 사용자의 입력
        st.chat_message("user").write(user_input)
        
        with st.chat_message("assistant"):
            # 멀티 에이전트 처리
            try:
                final_answer = multi_agent_query(
                    user_input, 
                    agents, 
                    coordinator, 
                    selected_model
                )
                
                st.markdown("### 📝 최종 답변")
                st.markdown(final_answer)
                
                # 대화기록 저장
                add_message("user", user_input)
                add_message("assistant", final_answer)
                
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
    else:
        warning_msg.error("먼저 'PDF 로드 및 에이전트 생성' 버튼을 클릭하여 시스템을 초기화하세요.")

