-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table: stores chunks with their embeddings
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type VARCHAR(50)  NOT NULL,  -- pdf | confluence | slack | drive
    source_id   VARCHAR(500) NOT NULL,  -- original file path or URL
    title       VARCHAR(1000),
    content     TEXT         NOT NULL,
    checksum    VARCHAR(64)  NOT NULL,  -- MD5 of content for dedup
    embedding   vector(1024),           -- fastembed BAAI/bge-m3
    metadata    JSONB        NOT NULL DEFAULT '{}',
    collection  VARCHAR(200) NOT NULL DEFAULT 'general',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Index for fast ANN search (HNSW — better recall than IVFFlat)
CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index for metadata filtering
CREATE INDEX IF NOT EXISTS documents_collection_idx ON documents (collection);
CREATE INDEX IF NOT EXISTS documents_source_type_idx ON documents (source_type);
CREATE INDEX IF NOT EXISTS documents_checksum_idx ON documents (checksum);

-- Full-text search index for BM25 hybrid search
CREATE INDEX IF NOT EXISTS documents_content_fts_idx
    ON documents USING gin (to_tsvector('french', content));

-- Query audit log (immutable — no UPDATE/DELETE)
CREATE TABLE IF NOT EXISTS query_logs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      VARCHAR(200),
    question     TEXT         NOT NULL,
    answer       TEXT,
    sources      JSONB        NOT NULL DEFAULT '[]',
    latency_ms   INTEGER,
    tokens_used  INTEGER,
    model        VARCHAR(100),
    collection   VARCHAR(200),
    feedback     SMALLINT,    -- 1 = thumbs up, -1 = thumbs down, NULL = no feedback
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS query_logs_user_idx ON query_logs (user_id);
CREATE INDEX IF NOT EXISTS query_logs_created_at_idx ON query_logs (created_at DESC);

-- Ingestion jobs tracking
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type  VARCHAR(50)  NOT NULL,
    source_id    VARCHAR(500) NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'pending',  -- pending | running | done | failed
    chunks_count INTEGER      DEFAULT 0,
    error        TEXT,
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
