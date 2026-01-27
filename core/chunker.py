"""
문서 청킹 모듈
토큰 기반 스마트 청킹 및 페이지 단위 청킹 지원
Gemini Vision 마크다운 변환 결과의 Dual Chunking 처리
"""
import re
import tiktoken
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import config


class DocumentChunker:
    """문서를 토큰 기반으로 청킹하고 overlap 메타데이터를 관리하는 클래스"""
    
    def __init__(
        self,
        chunk_size_tokens: int = None,
        overlap_tokens: int = None,
        separators: list = None
    ):
        """
        초기화
        
        Args:
            chunk_size_tokens: 청크 크기 (토큰 수)
            overlap_tokens: 오버랩 크기 (토큰 수)
            separators: 텍스트 분할 구분자 리스트
        """
        self.chunk_size_tokens = chunk_size_tokens or config.CHUNK_SIZE_TOKENS
        self.overlap_tokens = overlap_tokens or config.CHUNK_OVERLAP_TOKENS
        self.separators = separators or ["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        self._token_counter = self._get_token_counter()
    
    def _get_token_counter(self):
        """토큰 카운터 함수 반환"""
        encoding = tiktoken.get_encoding("cl100k_base")
        
        def count_tokens(text: str) -> int:
            return len(encoding.encode(text))
        
        return count_tokens
    
    def chunk_with_overlap_metadata(self, text: str) -> list:
        """
        overlap 정보를 메타데이터로 저장하는 스마트 청킹
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            chunks: 청크 정보 리스트 (overlap 메타데이터 포함)
        """
        # 빈 텍스트 처리
        if not text or not text.strip():
            return []
        
        chunks = []
        
        # RecursiveCharacterTextSplitter로 분할 (토큰 기반)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size_tokens,
            chunk_overlap=self.overlap_tokens,
            length_function=self._token_counter,
            separators=self.separators
        )
        
        temp_doc = Document(page_content=text)
        split_docs = text_splitter.split_documents([temp_doc])
        
        # 분할 결과가 비어있으면 빈 리스트 반환
        if not split_docs:
            return []
        
        for idx, doc in enumerate(split_docs):
            chunk_text = doc.page_content
            
            # 빈 청크는 건너뛰기
            if not chunk_text or not chunk_text.strip():
                continue
            
            # 원본 텍스트에서 청크 위치 찾기
            chunk_start = text.find(chunk_text[:100])
            if chunk_start == -1:
                if len(chunks) == 0:
                    # 첫 번째 유효한 청크
                    chunk_start = 0
                elif len(chunks) > 0:
                    # 이전 청크의 끝 위치 참고
                    try:
                        prev_end = chunks[-1].get("end_pos", 0)
                        overlap_chars = self.overlap_tokens * 3
                        chunk_start = max(0, prev_end - overlap_chars)
                    except (IndexError, KeyError):
                        chunk_start = 0
                else:
                    chunk_start = 0
            
            chunk_end = chunk_start + len(chunk_text)
            
            # 이전 청크와의 overlap 계산
            overlap_prev_text = ""
            overlap_prev_start = 0
            overlap_prev_end = 0
            if len(chunks) > 0:
                try:
                    prev_chunk = chunks[-1]
                    overlap_chars = self.overlap_tokens * 3
                    prev_start = prev_chunk.get("start_pos", 0)
                    prev_end = prev_chunk.get("end_pos", 0)
                    overlap_prev_start = max(prev_start, chunk_start - overlap_chars)
                    overlap_prev_end = min(prev_end, chunk_start + overlap_chars)
                    if overlap_prev_start < overlap_prev_end and overlap_prev_end <= len(text):
                        overlap_prev_text = text[overlap_prev_start:overlap_prev_end]
                except (IndexError, KeyError, TypeError):
                    # 이전 청크 정보가 없으면 overlap 없음
                    pass
            
            # 다음 청크와의 overlap 계산
            overlap_next_text = ""
            overlap_next_start = 0
            overlap_next_end = 0
            if idx < len(split_docs) - 1:
                overlap_chars = self.overlap_tokens * 3
                next_chunk_start = chunk_end - overlap_chars
                overlap_next_start = max(chunk_start, next_chunk_start)
                overlap_next_end = min(chunk_end, chunk_end + overlap_chars)
                if overlap_next_start < overlap_next_end and overlap_next_end <= len(text):
                    overlap_next_text = text[overlap_next_start:overlap_next_end]
            
            chunks.append({
                "content": chunk_text,
                "start_pos": chunk_start,
                "end_pos": chunk_end,
                "overlap_prev": {
                    "text": overlap_prev_text,
                    "start": overlap_prev_start,
                    "end": overlap_prev_end
                },
                "overlap_next": {
                    "text": overlap_next_text,
                    "start": overlap_next_start,
                    "end": overlap_next_end
                },
                "chunk_index": idx
            })
        
        return chunks
    
    def extract_table_summaries(self, markdown_text: str) -> list:
        """
        마크다운 텍스트에서 <table_summary> 태그를 추출
        
        Args:
            markdown_text: 마크다운 텍스트
            
        Returns:
            [(summary, start_pos, end_pos), ...] 리스트
        """
        pattern = r'<table_summary>(.*?)</table_summary>'
        matches = []
        
        for match in re.finditer(pattern, markdown_text, re.DOTALL):
            summary = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            matches.append((summary, start_pos, end_pos))
        
        return matches
    
    def extract_table_markdown(self, markdown_text: str, summary_end_pos: int) -> str:
        """
        <table_summary> 태그 다음에 오는 표의 마크다운 추출
        
        Args:
            markdown_text: 전체 마크다운 텍스트
            summary_end_pos: <table_summary> 태그의 끝 위치
            
        Returns:
            표의 마크다운 텍스트
        """
        # summary 태그 다음 부분부터 시작
        remaining_text = markdown_text[summary_end_pos:]
        
        # 표 시작 패턴 찾기 (| 로 시작하는 줄)
        lines = remaining_text.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            
            # 표 시작: | 로 시작하는 줄
            if '|' in stripped and not in_table:
                in_table = True
                table_lines.append(line)
            # 표 계속: | 가 있거나 빈 줄
            elif in_table:
                if '|' in stripped or stripped == '':
                    table_lines.append(line)
                else:
                    # 표 종료
                    break
        
        return '\n'.join(table_lines).strip()
    
    def chunk_markdown_with_dual_chunking(self, markdown_text: str, page_number: int = 0) -> list:
        """
        Gemini Vision으로 변환된 마크다운을 Dual Chunking 전략으로 처리
        
        [Dual Chunking 전략]
        - <table_summary> 태그가 있는 표:
          - 검색용: summary + 주변 텍스트
          - 원본: 전체 표 마크다운
        - 일반 텍스트:
          - 기존 청킹 방식 적용
        
        Args:
            markdown_text: Gemini Vision으로 변환된 마크다운 텍스트
            page_number: 페이지 번호 (메타데이터용)
            
        Returns:
            Document 리스트 (메타데이터 포함)
        """
        documents = []
        
        # 1단계: <table_summary> 태그 추출
        table_summaries = self.extract_table_summaries(markdown_text)
        
        if not table_summaries:
            # 표가 없으면 일반 텍스트로 처리
            if config.CHUNK_BY_PAGE:
                # 페이지 단위: 전체를 하나의 청크로
                doc = Document(
                    page_content=markdown_text,
                    metadata={
                        'page_number': page_number,
                        'type': 'text',
                        'chunk_type': 'page'
                    }
                )
                documents.append(doc)
            else:
                # 토큰 기반 청킹
                chunks = self.chunk_with_overlap_metadata(markdown_text)
                for chunk in chunks:
                    doc = Document(
                        page_content=chunk.get("content", ""),
                        metadata={
                            'page_number': page_number,
                            'type': 'text',
                            'chunk_type': 'token',
                            'chunk_index': chunk.get("chunk_index", 0),
                            **{k: v for k, v in chunk.items() if k != "content" and k != "chunk_index"}
                        }
                    )
                    documents.append(doc)
            return documents
        
        # 2단계: 표와 텍스트 분리 처리
        last_pos = 0
        
        for idx, (summary, start_pos, end_pos) in enumerate(table_summaries):
            # 표 이전 텍스트 처리
            if start_pos > last_pos:
                text_before = markdown_text[last_pos:start_pos].strip()
                if text_before:
                    # 일반 텍스트 청킹
                    if config.CHUNK_BY_PAGE:
                        doc = Document(
                            page_content=text_before,
                            metadata={
                                'page_number': page_number,
                                'type': 'text',
                                'chunk_type': 'page'
                            }
                        )
                        documents.append(doc)
                    else:
                        chunks = self.chunk_with_overlap_metadata(text_before)
                        for chunk in chunks:
                            doc = Document(
                                page_content=chunk.get("content", ""),
                                metadata={
                                    'page_number': page_number,
                                    'type': 'text',
                                    'chunk_type': 'token',
                                    'chunk_index': chunk.get("chunk_index", 0),
                                    **{k: v for k, v in chunk.items() if k != "content" and k != "chunk_index"}
                                }
                            )
                            documents.append(doc)
            
            # 표 처리 (Dual Chunking)
            table_markdown = self.extract_table_markdown(markdown_text, end_pos)
            
            # 주변 텍스트 추출 (검색용 컨텍스트)
            context_start = max(0, start_pos - 200)  # 앞 200자
            context_end = min(len(markdown_text), end_pos + len(table_markdown) + 200)  # 뒤 200자
            context_text = markdown_text[context_start:context_end]
            
            # 검색용 텍스트: summary + 주변 컨텍스트
            search_text = f"{summary}\n{context_text}"
            
            # 원본 표 마크다운 (태그 제거)
            raw_table = markdown_text[start_pos:end_pos + len(table_markdown)]
            raw_table = re.sub(r'<table_summary>.*?</table_summary>\s*', '', raw_table, flags=re.DOTALL)
            
            # 표 Document 생성
            doc = Document(
                page_content=search_text.strip(),  # 검색용: summary + 컨텍스트
                metadata={
                    'page_number': page_number,
                    'type': 'table',
                    'is_table': True,
                    'summary': summary,  # 표 요약
                    'raw_data': raw_table.strip(),  # 원본 표 마크다운
                    'table_index': idx
                }
            )
            documents.append(doc)
            
            last_pos = end_pos + len(table_markdown)
        
        # 마지막 표 이후 텍스트 처리
        if last_pos < len(markdown_text):
            text_after = markdown_text[last_pos:].strip()
            if text_after:
                if config.CHUNK_BY_PAGE:
                    doc = Document(
                        page_content=text_after,
                        metadata={
                            'page_number': page_number,
                            'type': 'text',
                            'chunk_type': 'page'
                        }
                    )
                    documents.append(doc)
                else:
                    chunks = self.chunk_with_overlap_metadata(text_after)
                    for chunk in chunks:
                        doc = Document(
                            page_content=chunk.get("content", ""),
                            metadata={
                                'page_number': page_number,
                                'type': 'text',
                                'chunk_type': 'token',
                                'chunk_index': chunk.get("chunk_index", 0),
                                **{k: v for k, v in chunk.items() if k != "content" and k != "chunk_index"}
                            }
                        )
                        documents.append(doc)
        
        return documents
    
    def merge_chunks_with_overlap(self, chunks: list) -> str:
        """
        overlap 정보를 사용하여 청크를 정확하게 병합
        
        Args:
            chunks: 병합할 청크 리스트
            
        Returns:
            merged_text: 병합된 텍스트
        """
        if not chunks:
            return ""
        
        if len(chunks) == 1:
            try:
                return chunks[0].get("content", "") if isinstance(chunks[0], dict) else str(chunks[0])
            except (IndexError, KeyError, TypeError):
                return ""
        
        try:
            merged = chunks[0].get("content", "") if isinstance(chunks[0], dict) else str(chunks[0])
        except (IndexError, KeyError, TypeError):
            return ""
        
        for i in range(1, len(chunks)):
            try:
                current = chunks[i] if i < len(chunks) else None
                prev = chunks[i-1] if i-1 >= 0 else None
                
                if current is None or prev is None:
                    continue
                
                if not isinstance(current, dict) or not isinstance(prev, dict):
                    # 딕셔너리가 아니면 그냥 추가
                    merged += str(current) if current else ""
                    continue
            
                prev_overlap_dict = prev.get("overlap_next", {})
                curr_overlap_dict = current.get("overlap_prev", {})
                prev_overlap = prev_overlap_dict.get("text", "") if isinstance(prev_overlap_dict, dict) else ""
                curr_overlap = curr_overlap_dict.get("text", "") if isinstance(curr_overlap_dict, dict) else ""
                
                if prev_overlap and curr_overlap:
                    if prev_overlap == curr_overlap:
                        overlap_len = len(prev_overlap)
                        current_content = current.get("content", "")
                        if len(current_content) > overlap_len:
                            merged += current_content[overlap_len:]
                        else:
                            merged += current_content
                    else:
                        if len(prev_overlap) > 0 and len(curr_overlap) > 0:
                            common_suffix = ""
                            for j in range(1, min(len(prev_overlap), len(curr_overlap)) + 1):
                                if prev_overlap[-j:] == curr_overlap[:j]:
                                    common_suffix = prev_overlap[-j:]
                            
                            current_content = current.get("content", "")
                            if common_suffix:
                                merged += current_content[len(common_suffix):]
                            else:
                                merged += current_content
                        else:
                            merged += current.get("content", "")
                else:
                    merged += current.get("content", "")
            except (IndexError, KeyError, TypeError) as e:
                # 오류 발생 시 현재 청크 내용만 추가
                try:
                    merged += str(current.get("content", "")) if isinstance(current, dict) else str(current)
                except:
                    pass
        
        return merged
    
    def chunk_by_page(self, pdf_path: str, original_start_page: int = None, original_end_page: int = None) -> list:
        """
        PDF를 페이지 단위로 청킹
        
        Args:
            pdf_path: PDF 파일 경로 (섹션 PDF 또는 원본 PDF)
            original_start_page: 원본 PDF에서의 시작 페이지 (1-based, None이면 섹션 PDF의 첫 페이지를 1로 간주)
            original_end_page: 원본 PDF에서의 끝 페이지 (1-based, None이면 섹션 PDF의 마지막 페이지 사용)
            
        Returns:
            chunks: 페이지별 청크 정보 리스트
        """
        chunks = []
        
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            
            # 원본 페이지 번호가 지정되지 않으면 섹션 PDF의 페이지 번호 사용
            if original_start_page is None:
                original_start_page = 1
            if original_end_page is None:
                original_end_page = total_pages
            
            # 섹션 PDF의 모든 페이지를 처리
            for section_page_idx in range(total_pages):  # 섹션 PDF 내 상대 인덱스 (0-based)
                try:
                    page = reader.pages[section_page_idx]
                    page_text = page.extract_text()
                    
                    # 빈 페이지는 건너뛰기
                    if not page_text or not page_text.strip():
                        continue
                    
                    # 원본 PDF에서의 실제 페이지 번호 계산
                    actual_page_number = original_start_page + section_page_idx
                    
                    # 페이지 단위 청크 생성
                    chunk_data = {
                        "content": page_text.strip(),
                        "start_pos": 0,
                        "end_pos": len(page_text),
                        "overlap_prev": {
                            "text": "",
                            "start": 0,
                            "end": 0
                        },
                        "overlap_next": {
                            "text": "",
                            "start": 0,
                            "end": 0
                        },
                        "chunk_index": section_page_idx,  # 섹션 내 상대 인덱스
                        "page_number": actual_page_number  # 원본 PDF에서의 실제 페이지 번호
                    }
                    chunks.append(chunk_data)
                    
                except Exception as e:
                    print(f"   ⚠️  페이지 {section_page_idx + 1} 추출 중 오류: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ⚠️  PDF 페이지 단위 청킹 중 오류: {e}")
            return []
        
        return chunks

