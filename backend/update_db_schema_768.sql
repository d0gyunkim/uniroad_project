-- Supabase DB 스키마 업데이트: Gemini 768차원 임베딩으로 변경
-- 실행 방법: Supabase Dashboard > SQL Editor에서 실행

-- 1. 기존 테이블 백업 (선택사항)
-- CREATE TABLE policy_documents_backup AS SELECT * FROM policy_documents;

-- 2. embedding 컬럼 삭제 및 재생성 (768차원으로)
ALTER TABLE policy_documents DROP COLUMN IF EXISTS embedding;
ALTER TABLE policy_documents ADD COLUMN embedding vector(768);

-- 3. 벡터 검색 함수 업데이트 (768차원으로)
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_threshold FLOAT DEFAULT 0.78,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
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

-- 4. 인덱스 재생성 (성능 향상)
CREATE INDEX IF NOT EXISTS policy_documents_embedding_idx
  ON policy_documents
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- 완료!
SELECT 'DB 스키마 업데이트 완료: embedding 컬럼이 768차원으로 변경되었습니다.' AS status;
