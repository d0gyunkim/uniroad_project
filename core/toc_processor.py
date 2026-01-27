"""
목차 처리 모듈
PDF의 목차를 감지하고 파싱하는 클래스
"""
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import streamlit as st
import config


class TOCProcessor:
    """목차 감지 및 파싱을 담당하는 클래스"""
    
    def __init__(self, model_name: str = None):
        """
        초기화
        
        Args:
            model_name: LLM 모델명 (기본값: config.DEFAULT_LLM_MODEL)
        """
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
        self.toc_keywords = ["목차", "차례", "contents", "table of contents", "index"]
    
    def detect_toc_pages(self, pdf_path: str, max_pages_to_check: int = 10) -> list:
        """
        PDF의 처음 몇 페이지에서 목차 페이지를 찾는 메서드 (Gemini LLM 사용)
        
        [원리]
        - PDF의 총 페이지 수 확인
        - 20페이지 이상이면 처음 10페이지만 확인
        - 각 페이지의 텍스트를 Gemini LLM으로 분석하여 목차 페이지인지 판단
        - 목차는 보통 문서 앞부분에 위치하므로 처음 10페이지만 확인
        
        Args:
            pdf_path: PDF 파일 경로
            max_pages_to_check: 확인할 최대 페이지 수 (기본값: 10)
            
        Returns:
            toc_pages: 목차 페이지 번호 리스트 (0-based index)
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # 20페이지 이상이면 처음 10페이지만 확인
        if total_pages >= 20:
            pages_to_check = min(10, total_pages)
        else:
            pages_to_check = min(max_pages_to_check, total_pages)
        
        toc_pages = []
        
        # 페이지별 텍스트 추출 (병렬 처리 전에 미리 추출)
        page_data = []
        for page_num in range(pages_to_check):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            
            # 빈 페이지는 건너뛰기
            if not page_text or not page_text.strip():
                continue
            
            # 페이지 텍스트가 너무 길면 앞부분만 사용 (토큰 절약)
            if len(page_text) > 2000:
                page_text = page_text[:2000] + "..."
            
            page_data.append({
                "page_num": page_num,
                "page_text": page_text
            })
        
        # 병렬 처리로 목차 페이지 판단
        def check_toc_page(page_info):
            """단일 페이지 목차 여부 판단 함수 (병렬 실행용)"""
            page_num = page_info["page_num"]
            page_text = page_info["page_text"]
            
            # LLM으로 목차 페이지인지 판단
            detection_prompt = ChatPromptTemplate.from_template("""
당신은 PDF 문서의 목차 페이지를 식별하는 전문가입니다.

아래는 PDF 문서의 {page_num}번째 페이지의 텍스트입니다. 이 페이지가 목차(차례, Table of Contents) 페이지인지 판단하세요.

**판단 기준:**
1. "목차", "차례", "Contents", "Table of Contents" 등의 제목이 있는가?
2. 섹션 제목과 페이지 번호가 나열되어 있는가?
3. 문서의 구조(챕터, 섹션 등)를 보여주는 목록 형태인가?

**출력 형식:**
- 목차 페이지이면: "YES"
- 목차 페이지가 아니면: "NO"
- 확실하지 않으면: "NO"

**페이지 텍스트:**
{page_text}

**판단 결과:**""")
            
            llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=0)
            chain = detection_prompt | llm | StrOutputParser()
            
            try:
                response = chain.invoke({
                    "page_num": page_num + 1,
                    "page_text": page_text
                })
                
                # 응답에서 YES/NO 추출
                response_upper = response.strip().upper()
                if "YES" in response_upper or "목차" in response_upper:
                    return {"page_num": page_num, "is_toc": True, "error": None}
                else:
                    return {"page_num": page_num, "is_toc": False, "error": None}
            except Exception as e:
                # 오류 발생 시 키워드 기반으로 fallback
                page_text_lower = page_text.lower()
                for keyword in self.toc_keywords:
                    if keyword in page_text_lower:
                        return {"page_num": page_num, "is_toc": True, "error": str(e)}
                return {"page_num": page_num, "is_toc": False, "error": str(e)}
        
        # ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_page = {
                executor.submit(check_toc_page, page_info): page_info
                for page_info in page_data
            }
            
            for future in as_completed(future_to_page):
                page_info = future_to_page[future]
                try:
                    result = future.result()
                    if result["is_toc"]:
                        toc_pages.append(result["page_num"])
                        print(f"   ✅ 페이지 {result['page_num'] + 1}: 목차 페이지로 판단됨")
                    if result["error"]:
                        print(f"   ⚠️  페이지 {result['page_num'] + 1} 분석 중 오류 (키워드 기반 fallback): {result['error']}")
                except Exception as e:
                    print(f"   ⚠️  페이지 {page_info['page_num'] + 1} 처리 중 오류: {e}")
        
        # 페이지 번호 순서대로 정렬
        toc_pages.sort()
        
        return toc_pages
    
    def parse_toc_structure(self, pdf_path: str, toc_pages: list) -> list:
        """
        목차 페이지를 LLM으로 분석하여 섹션 구조를 추출하는 메서드
        
        [원리]
        1. 목차 페이지의 텍스트를 추출
        2. LLM에게 JSON 형식으로 섹션 정보 추출 요청
        3. 각 섹션의 제목, 시작 페이지, 끝 페이지를 자동 파싱
        
        Args:
            pdf_path: PDF 파일 경로
            toc_pages: 목차 페이지 번호 리스트
            
        Returns:
            sections: 섹션 정보 리스트 또는 None (파싱 실패 시)
        """
        reader = PdfReader(pdf_path)
        
        # 목차 페이지 텍스트 추출
        toc_text = ""
        for page_num in toc_pages:
            page = reader.pages[page_num]
            toc_text += f"\n--- 페이지 {page_num + 1} ---\n"
            toc_text += page.extract_text()
        
        # LLM으로 목차 구조 파싱
        # 목차 구조 파싱만 더 빠른 모델(gemini-2.5-flash-lite) 사용
        parse_prompt = ChatPromptTemplate.from_template("""
# 임무

제공된 텍스트는 대학 입시 모집요강의 초반 페이지(1~10페이지 내외)이다.

이 텍스트에서 '목차', '차례', 'Contents', '전형 요약' 등의 목록을 찾아 섹션 정보를 추출하라.

# 추출 규칙 (매우 중요)

1. **섹션명(Title)**: 목차에 적힌 정확한 섹션 이름을 추출하라.

2. **시작 페이지(Start Page)**: 해당 섹션이 시작되는 페이지 번호를 정수로 추출하라.

3. **종료 페이지(End Page) 추론**: 

   - 현재 섹션의 종료 페이지는 **(다음 섹션의 시작 페이지 - 1)**로 계산하라.

   - 마지막 섹션의 경우, 문서의 끝이라고 판단되면 적절한 큰 숫자(예: 999) 혹은 문맥상 파악되는 마지막 페이지를 입력하라.

4. **노이즈 제거**: 목차와 관련 없는 헤더, 푸터, 인사말 등은 무시하라.

5. **계층 구조 평탄화**: 대분류, 소분류가 섞여 있어도 가능한 평탄한 리스트(Flat List)로 반환하되, '학생부종합전형' 같은 주요 전형 구분은 반드시 별도 섹션으로 분리되어야 한다.

# 예외 처리

- 목차에 페이지 번호가 명시되지 않은 경우, 바로 앞 섹션의 페이지 범위를 참고하거나 문맥을 통해 추정하라.

- 만약 명확한 목차 패턴을 찾을 수 없다면 빈 리스트 `[]`를 반환하라.

# 출력 형식 (Strict JSON)

반드시 아래 JSON 포맷으로만 출력하고, 마크다운(```json) 태그나 부가 설명은 포함하지 마라.

[
  {{
    "section_name": "전형 일정",
    "start_page": 3,
    "end_page": 4
  }},
  {{
    "section_name": "모집 단위 및 인원",
    "start_page": 5,
    "end_page": 7
  }},
  {{
    "section_name": "학생부교과(지역균형전형)",
    "start_page": 8,
    "end_page": 12
  }}
]

**목차 텍스트:**
{toc_text}

**JSON (마크다운 없이 순수 JSON만):**
""")
        
        # 목차 구조 파싱만 더 빠른 모델 사용 (속도 최적화)
        toc_parsing_model = "gemini-2.5-flash-lite"
        llm = ChatGoogleGenerativeAI(model=toc_parsing_model, temperature=0)
        chain = parse_prompt | llm | StrOutputParser()
        
        response = chain.invoke({"toc_text": toc_text})
        
        # JSON 추출 (코드 블록 제거)
        # 마크다운 코드 블록 제거
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        # JSON 배열 찾기
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                sections = json.loads(json_str)
                if sections and len(sections) > 0:
                    # 필드명 변환 (section_name -> title, start_page, end_page 유지)
                    formatted_sections = []
                    for section in sections:
                        formatted_section = {
                            "title": section.get("section_name", section.get("title", "")),
                            "start_page": section.get("start_page", 1),
                            "end_page": section.get("end_page", 999)
                        }
                        formatted_sections.append(formatted_section)
                    return formatted_sections
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON 파싱 오류: {str(e)}")
                print(f"응답 내용: {response[:500]}")
                if st:
                    st.warning(f"JSON 파싱 오류: {str(e)}")
        
        return None
    
    def create_default_sections(self, pdf_path: str) -> list:
        """
        목차를 찾지 못했을 때 페이지 수 기반으로 기본 섹션 생성
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            sections: 4등분된 섹션 리스트
        """
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
        
        return sections
    
    def validate_and_fix_sections(self, sections: list, pdf_path: str) -> list:
        """
        섹션의 페이지 범위를 검증하고 수정
        
        Args:
            sections: 섹션 리스트
            pdf_path: PDF 파일 경로
            
        Returns:
            validated_sections: 검증 및 수정된 섹션 리스트
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        for i, section in enumerate(sections):
            section["start_page"] = max(1, min(section.get("start_page", 1), total_pages))
            if i < len(sections) - 1:
                section["end_page"] = min(
                    section.get("end_page", total_pages),
                    sections[i+1]["start_page"] - 1
                )
            else:
                section["end_page"] = min(section.get("end_page", total_pages), total_pages)
        
        return sections

