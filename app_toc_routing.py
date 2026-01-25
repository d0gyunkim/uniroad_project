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
import json
import re
from PyPDF2 import PdfReader, PdfWriter
from unstructured.partition.pdf import partition_pdf
from langchain.docstore.document import Document

# API KEY 정보로드
load_dotenv()

# GEMINI_API_KEY를 GOOGLE_API_KEY로 매핑
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# 프로젝트 이름을 입력합니다.
logging.langsmith("[Project] TOC-Based Dynamic Routing RAG - Gemini")

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

if not os.path.exists(".cache/toc_sections"):
    os.mkdir(".cache/toc_sections")

st.title("📑 목차 기반 동적 라우팅 입시 컨설턴트")

# 처음 1번만 실행하기 위한 코드
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "toc_index" not in st.session_state:
    st.session_state["toc_index"] = None

if "pdf_path" not in st.session_state:
    st.session_state["pdf_path"] = None

if "section_cache" not in st.session_state:
    st.session_state["section_cache"] = {}  # {section_key: documents}

if "section_vectorstores" not in st.session_state:
    st.session_state["section_vectorstores"] = {}  # {section_key: vectorstore}

# 사이드바 생성
with st.sidebar:
    clear_btn = st.button("대화 초기화")
    
    # PDF 파일 업로드
    uploaded_file = st.file_uploader("원본 PDF 업로드", type=["pdf"])
    
    selected_model = "gemini-2.5-flash-lite"
    
    # 재시도 설정
    max_retries = st.slider("최대 재시도 횟수", min_value=1, max_value=5, value=3)
    
    st.markdown("---")
    st.markdown("### 📑 목차 기반 동적 라우팅")
    st.markdown("1. 원본 PDF 업로드")
    st.markdown("2. 목차 자동 감지 및 파싱")
    st.markdown("3. 쿼리별 관련 섹션 자동 선택")
    st.markdown("4. 해당 섹션만 동적 처리")
    st.markdown("5. **표 별도 분석 및 요약**")
    st.markdown("6. **품질 평가 및 재시도**")
    st.markdown("")
    st.markdown("✅ 사전 분할 불필요")
    st.markdown("✅ 동적 섹션 선택")
    st.markdown("✅ 표 구조 인식 및 요약")
    st.markdown("✅ 효율적 처리")
    
    st.markdown("---")
    st.markdown("### ⚙️ 시스템 상태")
    if st.session_state["toc_index"]:
        st.success(f"✅ 목차 인덱스 로드 완료")
        st.info(f"📄 섹션 수: {len(st.session_state['toc_index'])}개")
        with st.expander("📋 목차 보기"):
            for section in st.session_state["toc_index"]:
                st.markdown(f"**{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
    else:
        st.warning("⏳ PDF 업로드 대기 중")

# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages"]:
        st.chat_message(chat_message.role).write(chat_message.content)

# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages"].append(ChatMessage(role=role, content=message))

# 목차 페이지 감지
def detect_toc_pages(pdf_path, max_pages_to_check=10):
    """
    PDF의 처음 몇 페이지에서 목차 페이지를 찾음
    """
    reader = PdfReader(pdf_path)
    toc_keywords = ["목차", "차례", "contents", "table of contents", "index"]
    
    toc_pages = []
    
    # 처음 10페이지 확인
    for page_num in range(min(max_pages_to_check, len(reader.pages))):
        page = reader.pages[page_num]
        text = page.extract_text().lower()
        
        # 목차 키워드가 포함되어 있는지 확인
        for keyword in toc_keywords:
            if keyword in text:
                toc_pages.append(page_num)
                break
    
    return toc_pages

# 목차 구조 파싱 (LLM 사용)
def parse_toc_structure(pdf_path, toc_pages, model_name="gemini-2.5-flash-lite"):
    """
    목차 페이지를 LLM으로 분석하여 섹션 구조 추출
    """
    reader = PdfReader(pdf_path)
    
    # 목차 페이지 텍스트 추출
    toc_text = ""
    for page_num in toc_pages:
        page = reader.pages[page_num]
        toc_text += f"\n--- 페이지 {page_num + 1} ---\n"
        toc_text += page.extract_text()
    
    # LLM으로 목차 구조 파싱
    parse_prompt = ChatPromptTemplate.from_template("""
당신은 PDF 문서의 목차를 분석하는 전문가입니다.

아래는 PDF 문서의 목차 페이지입니다. 목차 구조를 분석하여 각 섹션의 제목과 페이지 범위를 추출하세요.

**출력 형식 (JSON):**
[
  {{"title": "섹션 제목", "start_page": 시작페이지번호, "end_page": 끝페이지번호}},
  ...
]

**규칙:**
1. 각 섹션의 제목을 정확히 추출하세요
2. 페이지 번호는 1부터 시작합니다 (0이 아닌)
3. 섹션의 시작 페이지와 끝 페이지를 추정하세요
4. 다음 섹션이 시작되기 전까지가 현재 섹션의 끝 페이지입니다
5. 마지막 섹션의 끝 페이지는 문서의 마지막 페이지로 설정하세요
6. JSON 형식만 출력하세요 (추가 설명 없이)

**목차 텍스트:**
{toc_text}

**JSON:**
""")
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    chain = parse_prompt | llm | StrOutputParser()
    
    response = chain.invoke({"toc_text": toc_text})
    
    # JSON 추출 (코드 블록 제거)
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            sections = json.loads(json_str)
            # 섹션이 비어있지 않은지 확인
            if sections and len(sections) > 0:
                return sections
        except json.JSONDecodeError as e:
            st.warning(f"JSON 파싱 오류: {str(e)}")
    
    # JSON 파싱 실패 시 None 반환
    return None

# 섹션 전처리 함수 (표 구조 인식, 임베딩 생성)
def preprocess_section(section, pdf_path, model_name="gemini-2.5-flash-lite"):
    """
    섹션을 전처리하여 벡터스토어 생성 (표 구조 인식 포함)
    """
    section_key = f"{section['start_page']}_{section['end_page']}"
    
    # 섹션 추출
    section_path = extract_pdf_section(
        pdf_path,
        section["start_page"],
        section["end_page"]
    )
    
    # Multi-modal 방식으로 표와 텍스트 분리 추출
    raw_elements = extract_pdf_elements_multimodal(section_path)
    texts, tables = categorize_elements(raw_elements)
    
    # 표가 있으면 요약 생성
    table_summaries = []
    if tables:
        table_summaries = generate_table_summaries(tables, model_name)
    
    # 텍스트와 표 요약 결합
    all_texts = texts + table_summaries
    
    # Document 객체로 변환
    docs = []
    for idx, text in enumerate(all_texts):
        doc = Document(
            page_content=text,
            metadata={
                'section_title': section['title'],
                'section_start': section['start_page'],
                'section_end': section['end_page'],
                'is_table': idx >= len(texts)  # 표 요약인지 표시
            }
        )
        docs.append(doc)
    
    # 텍스트 분할 (표 요약은 이미 요약된 상태이므로 분할하지 않음)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=600,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    
    # 텍스트만 분할하고, 표 요약은 그대로 유지
    split_docs = []
    for doc in docs:
        if doc.metadata.get('is_table', False):
            # 표 요약은 분할하지 않음
            split_docs.append(doc)
        else:
            # 텍스트는 분할
            split_text_docs = text_splitter.split_documents([doc])
            split_docs.extend(split_text_docs)
    
    # 모든 문서에 메타데이터 확인
    for doc in split_docs:
        if 'section_title' not in doc.metadata:
            doc.metadata['section_title'] = section['title']
            doc.metadata['section_start'] = section['start_page']
            doc.metadata['section_end'] = section['end_page']
    
    # 임베딩 생성
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(documents=split_docs, embedding=embeddings)
    
    return {
        "vectorstore": vectorstore,
        "documents": split_docs,
        "table_count": len(tables)
    }

# 목차 인덱스 생성 및 모든 섹션 전처리
@st.cache_resource(show_spinner="PDF 전처리 중... (목차 분석, 표 인식, 임베딩 생성)")
def build_toc_index_and_preprocess(pdf_path, _cache_key):
    """
    PDF의 목차를 분석하고 모든 섹션을 전처리하여 벡터스토어 생성
    """
    # 1단계: 목차 페이지 감지
    st.info("🔍 목차 페이지 감지 중...")
    toc_pages = detect_toc_pages(pdf_path)
    
    if not toc_pages:
        st.warning("⚠️ 목차 페이지를 찾을 수 없습니다. 페이지 수 기반 분할을 사용합니다.")
        # 페이지 수 기반 분할
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        sections_per_part = max(1, total_pages // 4)
        
        sections = []
        for i in range(4):
            start = i * sections_per_part + 1
            end = (i + 1) * sections_per_part if i < 3 else total_pages
            sections.append({
                "title": f"섹션 {i+1}",
                "start_page": start,
                "end_page": end
            })
    else:
        st.success(f"✅ 목차 페이지 발견: {[p+1 for p in toc_pages]}")
        
        # 2단계: 목차 구조 파싱
        st.info("📋 목차 구조 파싱 중...")
        sections = parse_toc_structure(pdf_path, toc_pages)
        
        if not sections:
            # 파싱 실패 시 페이지 수 기반 분할
            st.warning("⚠️ 목차 파싱 실패. 페이지 수 기반 분할을 사용합니다.")
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            sections_per_part = max(1, total_pages // 4)
            
            sections = []
            for i in range(4):
                start = i * sections_per_part + 1
                end = (i + 1) * sections_per_part if i < 3 else total_pages
                sections.append({
                    "title": f"섹션 {i+1}",
                    "start_page": start,
                    "end_page": end
                })
    
    # 페이지 범위 검증 및 수정
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    for i, section in enumerate(sections):
        # 페이지 번호가 1부터 시작하도록 보정
        section["start_page"] = max(1, min(section.get("start_page", 1), total_pages))
        if i < len(sections) - 1:
            section["end_page"] = min(section.get("end_page", total_pages), sections[i+1]["start_page"] - 1)
        else:
            section["end_page"] = min(section.get("end_page", total_pages), total_pages)
    
    st.success(f"✅ {len(sections)}개 섹션 추출 완료")
    
    # 3단계: 모든 섹션 전처리 (표 구조 인식, 임베딩 생성)
    st.info(f"📄 {len(sections)}개 섹션 전처리 중... (표 구조 인식 및 임베딩 생성)")
    
    section_data = {}
    for idx, section in enumerate(sections, 1):
        with st.spinner(f"섹션 {idx}/{len(sections)}: '{section['title']}' 처리 중..."):
            section_key = f"{section['start_page']}_{section['end_page']}"
            result = preprocess_section(section, pdf_path)
            
            section_data[section_key] = {
                "vectorstore": result["vectorstore"],
                "documents": result["documents"],
                "section": section,
                "table_count": result["table_count"]
            }
            
            table_info = f" (표 {result['table_count']}개)" if result['table_count'] > 0 else ""
            st.success(f"✅ 섹션 {idx} 완료: '{section['title']}'{table_info}")
    
    return {
        "sections": sections,
        "section_data": section_data
    }

# 특정 페이지 범위의 PDF 추출
def extract_pdf_section(pdf_path, start_page, end_page):
    """
    PDF에서 특정 페이지 범위만 추출하여 임시 파일로 저장
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    
    # 페이지는 0부터 시작하므로 -1
    for page_num in range(start_page - 1, min(end_page, len(reader.pages))):
        writer.add_page(reader.pages[page_num])
    
    # 임시 파일로 저장
    temp_path = f".cache/toc_sections/section_{start_page}_{end_page}.pdf"
    with open(temp_path, "wb") as output_file:
        writer.write(output_file)
    
    return temp_path

# Multi-modal PDF 처리 함수 (표와 텍스트 분리)
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

def generate_table_summaries(tables, model_name="gemini-2.5-flash-lite"):
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
    
    prompt = ChatPromptTemplate.from_template(prompt_text)
    model = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    summarize_chain = {"element": lambda x: x} | prompt | model | StrOutputParser()
    
    # 배치로 처리
    table_summaries = summarize_chain.batch(tables, {"max_concurrency": 3})
    
    return table_summaries

# 관련 섹션 찾기 (LLM 사용 - 사고 과정 포함)
def find_relevant_sections(question, toc_index, model_name="gemini-2.5-flash-lite"):
    """
    질문과 관련된 섹션을 찾음 (사고 과정 포함)
    """
    # 섹션 목록 생성
    sections_list = "\n".join([
        f"{idx+1}. {section['title']} (페이지 {section['start_page']}-{section['end_page']})"
        for idx, section in enumerate(toc_index)
    ])
    
    routing_prompt = ChatPromptTemplate.from_template("""
당신은 대학 입시 모집요강 문서의 목차를 분석하는 전문가입니다.

사용자의 질문을 분석하고, 답변을 찾기 위해 어떤 섹션을 확인해야 할지 생각해보세요.

**사용자 질문:**
{question}

**문서의 목차 (섹션 목록):**
{sections_list}

**분석 과정:**
1. 질문의 내용을 참고하여 어떤 섹션을 확인해야 할지 생각해보세요, 단 질문의 단적인 내용 뿐만 아니라, 사용자의 의도를 파악하세요
2. 각 섹션의 제목을 보고 질문과 관련이 있는지 판단하세요,단 질문의 키워드나 단어에만 집중하지 마세요
3. 관련 섹션을 선택하고 이유를 설명하세요

**출력 형식:**
사고 과정: [질문 분석 및 섹션 선택 이유]
선택한 섹션: [섹션 번호들, 쉼표로 구분, 예: 1, 3]

**예시:**
사고 과정: 질문이 "네오르네상스 전형 모집 인원"에 관한 것이므로, 전형 관련 섹션과 모집 인원 관련 섹션을 확인해야 합니다.
선택한 섹션: 1, 2

---
**분석:**
""")
    
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    chain = routing_prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "question": question,
        "sections_list": sections_list
    })
    
    # 사고 과정과 섹션 번호 추출
    thinking_process = ""
    if "사고 과정:" in response:
        thinking_part = response.split("사고 과정:")[1]
        if "선택한 섹션:" in thinking_part:
            thinking_process = thinking_part.split("선택한 섹션:")[0].strip()
        else:
            thinking_process = thinking_part.strip()
    
    # 섹션 번호 추출
    section_numbers = []
    if "선택한 섹션:" in response:
        section_part = response.split("선택한 섹션:")[1]
        for num_str in re.findall(r'\d+', section_part):
            num = int(num_str)
            if 1 <= num <= len(toc_index):
                section_numbers.append(num - 1)  # 0-based index
    else:
        # 직접 숫자 추출
        for num_str in re.findall(r'\d+', response):
            num = int(num_str)
            if 1 <= num <= len(toc_index):
                section_numbers.append(num - 1)
    
    # 최소 1개는 선택
    if not section_numbers:
        section_numbers = [0]  # 첫 번째 섹션 선택
    
    return section_numbers, thinking_process

# 답변 품질 평가
def evaluate_answer_quality(question, answer, model_name="gemini-2.5-flash-lite"):
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
    
    is_acceptable = "불합격" not in evaluation and "합격" in evaluation
    
    return {
        "is_acceptable": is_acceptable,
        "evaluation_text": evaluation
    }

# RAG 체인 생성
def create_rag_chain(retriever, model_name="gemini-2.5-flash-lite"):
    """
    RAG 체인 생성
    """
    prompt = load_prompt("prompts/pdf-rag.yaml", encoding="utf-8")
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain

# 질의응답 (재시도 로직 포함)
def query_with_retry(question, pdf_path, toc_index, model_name="gemini-2.5-flash-lite", max_retries=3):
    """
    목차 기반 동적 라우팅으로 질의응답 수행 (재시도 포함)
    """
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            st.warning(f"🔄 {attempt}번째 시도 중... (이전 답변 품질 개선 필요)")
        
        # 1단계: 관련 섹션 찾기 (사고 과정 포함)
        st.info(f"🤔 질문 분석 및 관련 섹션 탐색 중... (시도 {attempt}/{max_retries})")
        section_indices, thinking_process = find_relevant_sections(question, toc_index, model_name)
        
        selected_sections = [toc_index[idx] for idx in section_indices]
        
        # 사고 과정 및 선택된 섹션 표시
        with st.expander(f"🧠 질문 분석 및 섹션 선택 (시도 {attempt})"):
            st.markdown("**질문 분석:**")
            if thinking_process:
                st.markdown(thinking_process)
            else:
                st.markdown("질문을 분석하여 관련 섹션을 선택했습니다.")
            
            st.markdown("---")
            st.markdown("**선택된 섹션:**")
            for idx, section in enumerate(selected_sections, 1):
                st.markdown(f"{idx}. **{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
        
        # 2단계: 각 섹션별로 개별 검색 수행
        st.info(f"📄 선택된 {len(selected_sections)}개 섹션에서 개별 검색 중...")
        
        all_retrieved_docs = []  # 모든 섹션에서 검색된 문서들
        
        for section in selected_sections:
            section_key = f"{section['start_page']}_{section['end_page']}"
            
            # 이미 전처리된 섹션 데이터 사용
            if section_key in st.session_state["section_vectorstores"]:
                section_data = st.session_state["section_vectorstores"][section_key]
                section_vectorstore = section_data["vectorstore"]
                
                # 각 섹션별로 검색 수행
                with st.spinner(f"섹션 '{section['title']}' 검색 중..."):
                    try:
                        # MMR 검색으로 각 섹션에서 관련 문서 가져오기
                        section_retriever = section_vectorstore.as_retriever(
                            search_type="mmr",
                            search_kwargs={
                                "k": 10,  # 각 섹션당 10개씩 (여러 섹션이면 합쳐서 20개 정도)
                                "fetch_k": 30,
                                "lambda_mult": 0.8
                            }
                        )
                        
                        # 검색 수행
                        try:
                            section_docs = section_retriever.invoke(question)
                        except AttributeError:
                            try:
                                section_docs = section_retriever.get_relevant_documents(question)
                            except AttributeError:
                                # 직접 vectorstore에서 검색
                                section_docs = section_vectorstore.similarity_search_with_score(question, k=10)
                                if section_docs and isinstance(section_docs[0], tuple):
                                    section_docs = [doc for doc, score in section_docs]
                        
                        all_retrieved_docs.extend(section_docs)
                        st.success(f"✅ 섹션 '{section['title']}'에서 {len(section_docs)}개 문서 검색 완료")
                        
                    except Exception as e:
                        st.warning(f"⚠️ 섹션 '{section['title']}' 검색 중 오류: {str(e)}")
            else:
                st.warning(f"⚠️ 섹션 '{section['title']}'의 전처리 데이터를 찾을 수 없습니다.")
        
        if not all_retrieved_docs:
            st.error("검색된 문서가 없습니다.")
            return {
                "answer": "오류: 관련 문서를 찾을 수 없습니다.",
                "evidence": [],
                "selected_sections": selected_sections
            }
        
        # 3단계: 검색 결과 통합 및 중복 제거
        st.info(f"🔗 {len(all_retrieved_docs)}개 검색 결과 통합 중...")
        
        # 중복 제거 (같은 내용의 문서는 하나만 유지)
        seen_contents = set()
        unique_docs = []
        for doc in all_retrieved_docs:
            content_hash = hash(doc.page_content[:100])  # 처음 100자로 중복 판단
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_docs.append(doc)
        
        # 관련성 점수로 정렬 (이미 MMR로 정렬되어 있지만, 여러 섹션 결과를 통합했으므로 재정렬)
        # 상위 20개만 선택
        retrieved_docs = unique_docs[:20]
        
        st.success(f"✅ 총 {len(retrieved_docs)}개 문서 선택 완료")
        
        # 4단계: 통합된 컨텍스트로 답변 생성
        st.info("🤖 답변 생성 중...")
        
        # 통합된 문서들로 임시 벡터스토어 생성 (RAG 체인 사용을 위해)
        if retrieved_docs:
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            temp_vectorstore = FAISS.from_documents(documents=retrieved_docs, embedding=embeddings)
            
            retriever = temp_vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": len(retrieved_docs)}  # 모든 문서 사용
            )
            
            # RAG 체인으로 답변 생성
            chain = create_rag_chain(retriever, model_name)
            answer = chain.invoke(question)
        else:
            answer = "관련 문서를 찾을 수 없습니다."
        
        # 5단계: 품질 평가
        st.info("📊 답변 품질 평가 중...")
        quality_result = evaluate_answer_quality(question, answer, model_name)
        
        with st.expander("📋 품질 평가 결과"):
            st.markdown(quality_result["evaluation_text"])
        
        # 근거 문서 정보 수집
        evidence_docs = []
        for doc in retrieved_docs[:10]:  # 상위 10개만 표시
            # 문서의 메타데이터에서 페이지 정보 추출
            page_info = ""
            section_info = ""
            
            if hasattr(doc, 'metadata') and doc.metadata:
                # 표 여부 확인
                is_table = doc.metadata.get('is_table', False)
                table_label = " [표 요약]" if is_table else ""
                
                # 섹션 정보
                if 'section_title' in doc.metadata:
                    section_info = doc.metadata['section_title']
                    if 'section_start' in doc.metadata and 'section_end' in doc.metadata:
                        page_info = f"섹션: {section_info} (페이지 {doc.metadata['section_start']}-{doc.metadata['section_end']}){table_label}"
                    else:
                        page_info = f"섹션: {section_info}{table_label}"
                elif 'page' in doc.metadata:
                    page_num = doc.metadata['page']
                    if isinstance(page_num, int):
                        page_info = f"페이지 {page_num + 1}"  # 0-based to 1-based
                    else:
                        page_info = f"페이지 {page_num}"
                elif 'source' in doc.metadata:
                    # 파일명에서 페이지 범위 추출 시도
                    source = doc.metadata['source']
                    if 'section_' in source:
                        # section_10_25.pdf 형식에서 추출
                        match = re.search(r'section_(\d+)_(\d+)', source)
                        if match:
                            page_info = f"페이지 {match.group(1)}-{match.group(2)}"
            
            evidence_docs.append({
                "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                "page_info": page_info,
                "section_info": section_info,
                "full_content": doc.page_content,
                "is_table": doc.metadata.get('is_table', False) if hasattr(doc, 'metadata') and doc.metadata else False
            })
        
        # 품질이 적절하면 반환
        if quality_result["is_acceptable"]:
            if attempt > 1:
                st.success(f"✅ {attempt}번째 시도에서 적절한 답변을 생성했습니다!")
            return {
                "answer": answer,
                "evidence": evidence_docs,
                "selected_sections": selected_sections
            }
        else:
            if attempt < max_retries:
                st.warning(f"⚠️ 답변 품질이 부족합니다. 재시도합니다... ({attempt}/{max_retries})")
            else:
                st.warning(f"⚠️ 최대 재시도 횟수({max_retries})에 도달했습니다. 현재 답변을 반환합니다.")
                return {
                    "answer": answer,
                    "evidence": evidence_docs,
                    "selected_sections": selected_sections
                }
    
    return {
        "answer": answer,
        "evidence": [],
        "selected_sections": []
    }

# PDF 업로드 처리
if uploaded_file:
    current_pdf = st.session_state.get("pdf_path")
    if current_pdf is None or current_pdf != f".cache/files/{uploaded_file.name}":
        # 파일 저장
        file_content = uploaded_file.read()
        pdf_path = f".cache/files/{uploaded_file.name}"
        with open(pdf_path, "wb") as f:
            f.write(file_content)
        
        st.session_state["pdf_path"] = pdf_path
        st.session_state["section_cache"] = {}  # 캐시 초기화
        st.session_state["section_vectorstores"] = {}  # 벡터스토어 캐시 초기화
        
        # 목차 인덱스 생성 및 모든 섹션 전처리
        result = build_toc_index_and_preprocess(pdf_path, uploaded_file.name)
        
        # 목차 인덱스 저장
        st.session_state["toc_index"] = result["sections"]
        
        # 각 섹션의 벡터스토어 저장
        for section_key, data in result["section_data"].items():
            st.session_state["section_vectorstores"][section_key] = data
        
        st.success("✅ PDF 업로드 및 전처리 완료! (목차 분석, 표 인식, 임베딩 생성)")
        st.rerun()

# 초기화 버튼
if clear_btn:
    st.session_state["messages"] = []

# 이전 대화 기록 출력
print_messages()

# 사용자 입력
user_input = st.chat_input("입시 관련 질문을 해주세요!")

warning_msg = st.empty()

# 질의응답 처리
if user_input:
    toc_index = st.session_state.get("toc_index")
    pdf_path = st.session_state.get("pdf_path")
    
    if toc_index and pdf_path:
        st.chat_message("user").write(user_input)
        
        with st.chat_message("assistant"):
            try:
                result = query_with_retry(
                    user_input,
                    pdf_path,
                    toc_index,
                    selected_model,
                    max_retries
                )
                
                # 결과가 딕셔너리인지 확인 (새 형식)
                if isinstance(result, dict):
                    answer = result["answer"]
                    evidence = result.get("evidence", [])
                    selected_sections = result.get("selected_sections", [])
                else:
                    # 이전 형식 호환성
                    answer = result
                    evidence = []
                    selected_sections = []
                
                st.markdown("### 📝 답변")
                st.markdown(answer)
                
                # 근거 문서 표시
                if evidence:
                    st.markdown("---")
                    st.markdown("### 📚 답변 근거 (검색된 문서)")
                    st.caption(f"총 {len(evidence)}개의 관련 문서 청크를 참고했습니다.")
                    
                    for idx, doc in enumerate(evidence, 1):
                        expander_title = f"📄 근거 {idx}"
                        if doc['is_table']:
                            expander_title = f"📊 표 요약 {idx}"
                        if doc['page_info']:
                            expander_title += f" - {doc['page_info']}"
                        
                        with st.expander(expander_title):
                            if doc['is_table']:
                                st.markdown("**표 요약 내용:**")
                                st.info("이 내용은 PDF의 표를 AI가 분석하여 요약한 것입니다.")
                            else:
                                st.markdown("**문서 내용:**")
                            st.markdown(doc['content'])
                            if doc['page_info']:
                                st.caption(f"📍 출처: {doc['page_info']}")
                            if len(doc['full_content']) > 500:
                                with st.expander("전체 내용 보기"):
                                    st.markdown(doc['full_content'])
                
                # 선택된 섹션 정보 표시
                if selected_sections:
                    st.markdown("---")
                    st.markdown("### 📋 참고한 섹션")
                    for section in selected_sections:
                        st.markdown(f"- **{section['title']}** (페이지 {section['start_page']}-{section['end_page']})")
                
                add_message("user", user_input)
                add_message("assistant", answer)
                
            except Exception as e:
                import traceback
                st.error(f"오류 발생: {str(e)}")
                with st.expander("상세 오류 정보"):
                    st.code(traceback.format_exc())
    else:
        if not pdf_path:
            warning_msg.error("먼저 PDF를 업로드해주세요.")
        elif not toc_index:
            warning_msg.error("PDF 목차 분석이 완료되지 않았습니다. 잠시 후 다시 시도해주세요.")

