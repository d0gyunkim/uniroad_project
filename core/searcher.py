"""
검색 엔진 모듈
단순 벡터 기반 유사도 검색 기능
"""
from langchain.docstore.document import Document
import config


class SearchEngine:
    """벡터 기반 유사도 검색을 담당하는 클래스"""
    
    def __init__(self):
        """
        초기화
        """
        pass
    
    def hybrid_search(
        self,
        question: str,
        vectorstore,
        documents: list,
        top_k: int = 10
    ) -> list:
        """
        단순 벡터 기반 유사도 검색
        
        Args:
            question: 사용자 질문
            vectorstore: FAISS 벡터스토어
            documents: 문서 리스트 (사용하지 않음, 호환성을 위해 유지)
            top_k: 반환할 상위 문서 수
            
        Returns:
            [(Document, score), ...] 형태의 리스트
        """
        # 단순 벡터 검색으로 많이 가져오기
        try:
            # similarity_search_with_score로 점수와 함께 검색
            vector_results = vectorstore.similarity_search_with_score(question, k=top_k)
            
            # 거리 점수를 유사도 점수로 변환 (거리가 작을수록 유사도 높음)
            # FAISS는 L2 거리를 반환하므로, 1 / (1 + distance)로 변환
            vector_docs_with_scores = [
                (doc, 1.0 / (1.0 + score))  # 거리를 유사도로 변환
                for doc, score in vector_results
            ]
        except Exception as e:
            # 오류 발생 시 빈 리스트 반환
            vector_docs_with_scores = []
        
        return vector_docs_with_scores

