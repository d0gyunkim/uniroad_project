"""
RAG 관련 Pydantic 모델
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class SearchResult(BaseModel):
    """RAG 검색 결과"""
    found: bool = Field(description="문서 발견 여부")
    chunks: List[Dict] = Field(default_factory=list, description="검색된 청크 목록")
    source: str = Field(default="", description="출처 정보")
    logs: List[str] = Field(default_factory=list, description="검색 과정 로그")


class ClassificationResult(BaseModel):
    """문서 분류 결과"""
    category: str = Field(description="문서 카테고리")
    confidence: float = Field(ge=0.0, le=1.0, description="신뢰도 (0~1)")
    reason: str = Field(description="분류 이유")
    keywords: List[str] = Field(default_factory=list, description="키워드 목록")


class DocumentMetadata(BaseModel):
    """문서 메타데이터"""
    title: str = Field(description="문서 제목")
    source: str = Field(description="출처")
    fileName: str = Field(description="파일명")
    category: str = Field(description="카테고리")
    categoryName: str = Field(description="카테고리 한글명")
    confidence: float = Field(description="분류 신뢰도")
    classificationReason: str = Field(description="분류 이유")
    keywords: List[str] = Field(description="키워드")
    summary: str = Field(description="요약본")
    totalPages: int = Field(description="총 페이지 수")
    parseMethod: str = Field(description="파싱 방법")
    chunkIndex: Optional[int] = Field(None, description="청크 인덱스")
    totalChunks: Optional[int] = Field(None, description="총 청크 수")
