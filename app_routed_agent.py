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

# API KEY 정보로드
load_dotenv()

# GEMINI_API_KEY를 GOOGLE_API_KEY로 매핑
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 프로젝트 이름을 입력합니다.
logging.langsmith("[Project] Routed Agent RAG - Gemini")

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

st.title("🎯 라우팅 기반 입시 컨설턴트")

# 처음 1번만 실행하기 위한 코드
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "agents" not in st.session_state:
    st.session_state["agents"] = None

# 사이드바 생성
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    
    # 분할 PDF 폴더 경로
    pdf_folder = st.text_input(
        "분할 PDF 폴더 경로",
        value="경희대_수시요강_분할표"
    )
    
    load_btn = st.button("PDF 로드 및 에이전트 생성")
    
    selected_model = "gemini-2.5-flash-lite"
    
    st.markdown("---")
    st.markdown("### 🎯 하이브리드 시스템")
    st.markdown("1. 질문 분석 (라우팅)")
    st.markdown("2. 관련 문서 자동 선택")
    st.markdown("3. 각 문서별 에이전트 답변")
    st.markdown("4. 코디네이터가 정보 종합")
    st.markdown("")
    st.markdown("⚡ 효율 + 완전한 정보 통합")
    
    st.markdown("---")
    st.markdown("### ⚙️ 시스템 상태")
    if st.session_state["agents"]:
        st.success(f"✅ {len(st.session_state['agents'])}개 문서 로드")
    else:
        st.warning("⏳ 문서 대기 중")

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
    
    # 검색기 생성 (라우팅용 - 빠른 검색)
    retriever_routing = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}  # 라우팅용은 적은 수
    )
    
    # 검색기 생성 (답변용 - 상세 검색)
    retriever_answer = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 20,
            "fetch_k": 50,
            "lambda_mult": 0.8
        }
    )
    
    return {
        "name": pdf_name,
        "path": pdf_path,
        "retriever_routing": retriever_routing,
        "retriever_answer": retriever_answer,
        "vectorstore": vectorstore
    }

# 멀티 에이전트 로드 (캐시 버전 2 - retriever_answer 포함)
@st.cache_resource(show_spinner="문서 로드 중...")
def load_agents(folder_path, _cache_version=2):
    """
    폴더 내 모든 PDF를 로드하여 에이전트 생성
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
        with st.spinner(f"문서 {idx}/{len(pdf_files)} 처리 중... ({pdf_file.name})"):
            agent = embed_single_pdf(str(pdf_file), pdf_file.stem)
            agents.append(agent)
            st.success(f"✅ 문서 {idx} 준비 완료: {pdf_file.name}")
    
    return agents

# 라우터: 질문과 가장 관련있는 문서 찾기
def route_to_relevant_docs(question, agents, top_k=2):
    """
    질문과 가장 관련있는 문서를 찾는 라우터
    """
    st.info("🔍 질문 분석 및 관련 문서 탐색 중...")
    
    doc_scores = []
    
    # 각 문서에서 관련성 점수 계산
    for agent in agents:
        # 빠른 검색으로 관련성 확인
        docs = agent["retriever_routing"].get_relevant_documents(question)
        
        # 검색된 문서 수와 내용 길이로 점수 계산
        if docs:
            # 관련성 점수 = 검색된 문서 수 + 평균 문서 길이
            avg_length = sum(len(doc.page_content) for doc in docs) / len(docs)
            score = len(docs) * avg_length
        else:
            score = 0
        
        doc_scores.append({
            "agent": agent,
            "score": score,
            "sample_content": docs[0].page_content[:200] if docs else ""
        })
    
    # 점수로 정렬
    doc_scores.sort(key=lambda x: x["score"], reverse=True)
    
    # 상위 top_k 문서 선택
    selected_agents = [item["agent"] for item in doc_scores[:top_k]]
    
    # 선택된 문서 표시
    with st.expander("📋 선택된 관련 문서"):
        for idx, item in enumerate(doc_scores[:top_k], 1):
            st.markdown(f"**{idx}. {item['agent']['name']}**")
            st.markdown(f"관련성 점수: {item['score']:.0f}")
            st.markdown(f"샘플: {item['sample_content'][:150]}...")
            st.markdown("---")
    
    return selected_agents

# 단일 에이전트 답변 생성
def create_agent_answer(question, agent, model_name="gemini-2.5-flash-lite"):
    """
    단일 에이전트가 자신의 문서에서 답변 생성
    """
    # 에이전트 구조 확인
    if "retriever_answer" not in agent:
        raise ValueError(f"에이전트 '{agent.get('name', 'unknown')}'에 'retriever_answer'가 없습니다. 문서를 다시 로드해주세요.")
    
    # 문서에서 관련 정보 검색
    docs = agent["retriever_answer"].get_relevant_documents(question)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # 에이전트 전용 프롬프트
    from langchain_teddynote.prompts import load_prompt
    prompt = load_prompt("prompts/pdf-rag-agent.yaml", encoding="utf-8")
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    
    # 체인 구성
    chain = prompt | llm | StrOutputParser()
    
    # 프롬프트에 필요한 변수 전달
    response = chain.invoke({
        "context": context,
        "question": question
    })
    
    return response

# 선택된 문서에서 각 에이전트 답변 생성
def generate_answers_from_selected_agents(question, selected_agents, model_name="gemini-2.5-flash-lite"):
    """
    선택된 각 문서에 대해 독립적인 에이전트가 답변 생성
    """
    st.info(f"🤖 선택된 {len(selected_agents)}개 문서에서 각각 답변 생성 중...")
    
    agent_responses = []
    
    # 각 에이전트가 독립적으로 답변
    for idx, agent in enumerate(selected_agents, 1):
        with st.spinner(f"에이전트 {idx}/{len(selected_agents)} 답변 생성 중... ({agent['name']})"):
            response = create_agent_answer(question, agent, model_name)
            agent_responses.append({
                "agent_name": agent["name"],
                "response": response
            })
            st.success(f"✅ 에이전트 {idx} 답변 완료: {agent['name']}")
    
    return agent_responses

# 코디네이터: 에이전트 정보 종합
def synthesize_agent_answers(question, agent_responses, model_name="gemini-2.5-flash-lite"):
    """
    여러 에이전트의 답변을 종합하여 완전한 답변 생성
    """
    st.info("🎯 코디네이터가 정보 종합 중...")
    
    # 에이전트 답변들 표시 (펼침 가능)
    with st.expander("🔍 각 에이전트 답변 보기"):
        for idx, response in enumerate(agent_responses, 1):
            st.markdown(f"**[에이전트 {idx}: {response['agent_name']}]**")
            st.markdown(response['response'])
            st.markdown("---")
    
    # 종합 프롬프트
    synthesizer_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 전문 컨설턴트이며, 여러 에이전트의 정보를 종합하는 코디네이터입니다.

각 에이전트가 자신의 문서를 기반으로 질문에 답변했습니다.
당신의 역할은 이 답변들을 종합하여 학생에게 완전하고 체계적인 답변을 제공하는 것입니다.

**정보 출처 규칙 (엄격):**
1. 오직 에이전트들이 문서에서 찾은 구체적인 정보만 사용하세요
2. 에이전트가 "찾을 수 없다"고 한 정보는 추측하지 마세요
3. 외부 지식으로 구체적인 수치나 정보를 보충하지 마세요
4. 여러 에이전트의 정보를 통합하되, 숫자 정보는 절대 임의로 더하지 말고, 각 에이전트의 답변에 있는 숫자를 사용하세요.

**종합 규칙:**
1. **중복 제거**: 같은 정보가 여러 에이전트에 있으면 한 번만 언급하세요
2. **정보 통합**: 보완적인 정보는 논리적으로 연결하여 통합하세요
3. **체계적 구성**: 정보를 논리적 순서로 정리하세요 (예: 전형 개요 → 세부사항 → 조건)
4. **완전성**: 모든 에이전트의 관련 정보를 빠짐없이 포함하세요
5. **명확성**: 학생과 학부모가 이해하기 쉽게 친절하고 명확하게 설명하세요

**답변 구성:**
1. 질문에 대한 핵심 답변을 먼저 제시하세요
2. 세부 정보를 체계적으로 정리하세요 (목록, 표 등 활용)
3. 여러 에이전트에서 나온 보완 정보를 자연스럽게 통합하세요
4. 정보가 부족한 부분이 있다면 명시하세요

**중요:**
- 에이전트들의 정보를 있는 그대로 사용하되, 자연스럽게 통합하세요
- 새로운 정보를 만들어내지 마세요
- 모든 구체적 정보(숫자, 날짜, 이름 등)는 에이전트 답변에서만 가져오세요

---

**학생 질문:**
{question}

---

**에이전트 답변들:**

{agent_responses}

---

**종합 답변:**
(여러 에이전트의 정보를 종합하여 완전하고 체계적인 답변을 작성하세요)
""")
    
    # 에이전트 답변들을 포맷팅
    formatted_responses = "\n\n".join([
        f"[에이전트 {idx}: {resp['agent_name']}]\n{resp['response']}"
        for idx, resp in enumerate(agent_responses, 1)
    ])
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    chain = synthesizer_prompt | llm | StrOutputParser()
    
    synthesized_response = chain.invoke({
        "question": question,
        "agent_responses": formatted_responses
    })
    
    return synthesized_response

# PDF 로드 버튼이 눌리면
if load_btn:
    # 캐시 초기화 (이전 버전 제거)
    if hasattr(st, 'cache_resource'):
        # 캐시 클리어를 위한 플래그
        st.session_state["clear_cache"] = True
    
    agents = load_agents(pdf_folder)
    if agents:
        # 에이전트 구조 검증
        for agent in agents:
            if "retriever_answer" not in agent:
                st.error(f"에이전트 '{agent.get('name', 'unknown')}' 구조 오류. 캐시를 초기화하고 다시 시도해주세요.")
                st.stop()
        
        st.session_state["agents"] = agents
        st.success(f"🎉 시스템 준비 완료! ({len(agents)}개 문서)")
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
    
    if agents:
        # 에이전트 구조 검증
        for agent in agents:
            if "retriever_answer" not in agent:
                warning_msg.error("에이전트 구조 오류가 감지되었습니다. 'PDF 로드 및 에이전트 생성' 버튼을 다시 클릭해주세요.")
                st.stop()
        
        # 사용자의 입력
        st.chat_message("user").write(user_input)
        
        with st.chat_message("assistant"):
            try:
                # 단계 1: 관련 문서 라우팅 (상위 2개 선택)
                selected_agents = route_to_relevant_docs(user_input, agents, top_k=2)
                
                st.success(f"✅ {len(selected_agents)}개 관련 문서 선택 완료")
                
                # 단계 2: 각 선택된 문서에 대해 독립적인 에이전트 답변 생성
                agent_responses = generate_answers_from_selected_agents(
                    user_input,
                    selected_agents,
                    selected_model
                )
                
                # 단계 3: 코디네이터가 정보 종합
                final_answer = synthesize_agent_answers(
                    user_input,
                    agent_responses,
                    selected_model
                )
                
                st.markdown("### 📝 종합 답변")
                st.markdown(final_answer)
                
                # 대화기록 저장
                add_message("user", user_input)
                add_message("assistant", final_answer)
                
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
    else:
        warning_msg.error("먼저 'PDF 로드 및 에이전트 생성' 버튼을 클릭하여 시스템을 초기화하세요.")

