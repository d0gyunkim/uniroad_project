-- Supabase 벡터 검색 함수
-- 이 SQL을 Supabase SQL Editor에서 실행하세요!

-- 1. pgvector 확장 활성화 (이미 되어있을 수도 있음)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 벡터 검색 함수 생성
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    policy_documents.id,
    policy_documents.content,
    policy_documents.metadata,
    1 - (policy_documents.embedding <=> query_embedding) AS similarity
  FROM policy_documents
  WHERE 1 - (policy_documents.embedding <=> query_embedding) > match_threshold
  ORDER BY policy_documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 3. 함수 사용 권한 부여
GRANT EXECUTE ON FUNCTION match_documents TO authenticated, anon;

-- 4. 테스트 쿼리 (예시)
-- SELECT * FROM match_documents(
--   (SELECT embedding FROM policy_documents LIMIT 1),
--   0.5,
--   3
-- );

