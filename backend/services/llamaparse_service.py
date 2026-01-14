"""
LlamaParse PDF 파싱 서비스 (페이지 병렬 처리)
"""
from llama_parse import LlamaParse
from config import settings
from config.logging_config import setup_logger
import asyncio
from typing import Optional, List
import tempfile
import os

logger = setup_logger('llamaparse')


class LlamaParseService:
    """LlamaParse를 사용한 PDF 파싱 (페이지 병렬 처리)"""

    def __init__(self):
        self.parser = LlamaParse(
            api_key=settings.LLAMA_API_KEY,
            result_type="markdown",
            parsing_instruction="한국어 대학 입시 문서입니다. 모든 텍스트, 표, 구조화된 데이터를 정확하게 추출하세요. 한글 문자와 서식을 보존하세요.",
            premium_mode=True,
            language="ko"
        )

    def _parse_page_range_sync(
        self,
        file_path: str,
        start_page: int,
        end_page: int,
        chunk_id: int,
        api_key: str
    ) -> tuple:
        """
        특정 페이지 범위를 파싱 (병렬 처리용)

        Args:
            file_path: PDF 파일 경로
            start_page: 시작 페이지 (0부터 시작)
            end_page: 끝 페이지
            chunk_id: 청크 ID (로깅용)

        Returns:
            (chunk_id, markdown_text)
        """
        try:
            # 별도 프로세스에서 실행되므로 새로운 parser 인스턴스 생성
            from llama_parse import LlamaParse

            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                premium_mode=True,
                language="ko"
            )

            # PyPDF로 페이지 분리
            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(file_path)
            writer = PdfWriter()

            # 페이지 범위 추출
            for page_num in range(start_page, min(end_page + 1, len(reader.pages))):
                writer.add_page(reader.pages[page_num])

            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as chunk_file:
                writer.write(chunk_file)
                chunk_path = chunk_file.name

            try:
                # 동기 파싱 (별도 프로세스에서 실행)
                documents = parser.load_data(chunk_path)

                markdown = "\n\n".join([doc.text for doc in documents])

                return (chunk_id, markdown)

            finally:
                os.unlink(chunk_path)

        except Exception as e:
            return (chunk_id, "")
    
    async def parse_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        max_pages: Optional[int] = None,
        pages_per_chunk: int = 10  # 한 번에 처리할 페이지 수
    ) -> dict:
        """
        PDF를 마크다운으로 변환 (페이지 병렬 처리)

        Args:
            file_bytes: PDF 파일 바이트
            filename: 파일명
            max_pages: 최대 처리 페이지 (테스트용)
            pages_per_chunk: 청크당 페이지 수 (기본 10페이지씩 병렬 처리)

        Returns:
            {
                'markdown': str,
                'totalPages': int,
                'processingTime': float
            }
        """
        import time
        from pypdf import PdfReader

        start_time = time.time()

        logger.info(f"🚀 LlamaParse 병렬 파싱 시작: {filename}")
        logger.info(f"📦 파일 크기: {len(file_bytes) / 1024 / 1024:.2f}MB")

        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name

            try:
                # 페이지 수 확인
                reader = PdfReader(tmp_path)
                total_pages = len(reader.pages)

                # 테스트 모드
                if max_pages and max_pages < total_pages:
                    total_pages = max_pages
                    logger.info(f"⚠️  테스트 모드: {max_pages}페이지만 처리")

                logger.info(f"📄 총 {total_pages}페이지 → {pages_per_chunk}페이지씩 병렬 처리")

                # 페이지 청크로 분할
                chunks: List[tuple] = []
                for i in range(0, total_pages, pages_per_chunk):
                    start = i
                    end = min(i + pages_per_chunk - 1, total_pages - 1)
                    chunk_id = i // pages_per_chunk + 1
                    chunks.append((tmp_path, start, end, chunk_id))

                logger.info(f"⚡ {len(chunks)}개 청크 병렬 처리 시작...")

                # ProcessPoolExecutor로 진짜 병렬 실행
                import concurrent.futures
                from config import settings

                loop = asyncio.get_event_loop()

                with concurrent.futures.ProcessPoolExecutor() as executor:
                    futures = [
                        loop.run_in_executor(
                            executor,
                            self._parse_page_range_sync,
                            path, start, end, chunk_id, settings.LLAMA_API_KEY
                        )
                        for path, start, end, chunk_id in chunks
                    ]

                    results = await asyncio.gather(*futures)

                # 결과 정렬 및 병합 (청크 순서대로)
                results.sort(key=lambda x: x[0])  # chunk_id로 정렬
                markdown = "\n\n".join([text for _, text in results if text])

            finally:
                # 임시 파일 삭제
                os.unlink(tmp_path)

            processing_time = time.time() - start_time

            logger.info(f"✅ 파싱 완료!")
            logger.info(f"📝 결과 크기: {len(markdown) / 1024:.2f}KB")
            logger.info(f"⏱️  처리 시간: {processing_time:.2f}초 ({len(chunks)}개 청크 병렬)")

            return {
                'markdown': markdown,
                'totalPages': total_pages,
                'processingTime': processing_time
            }

        except Exception as e:
            logger.error(f"❌ LlamaParse 오류: {e}")
            raise Exception(f"PDF 파싱 실패: {str(e)}")


# 전역 인스턴스
llamaparse_service = LlamaParseService()

