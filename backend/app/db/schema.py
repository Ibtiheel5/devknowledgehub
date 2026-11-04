"""Schéma Postgres de la plateforme. Idempotent : peut être rejoué à chaque démarrage."""
import psycopg

from app.config import settings


def schema_sql(dim: int) -> str:
    return f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS repositories (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    git_url     TEXT,
    indexed_at  TIMESTAMPTZ
);

ALTER TABLE repositories ADD COLUMN IF NOT EXISTS commit_sha TEXT;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS source_type TEXT;

CREATE TABLE IF NOT EXISTS chunks (
    id          BIGSERIAL PRIMARY KEY,
    repo_id     INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,
    kind        TEXT NOT NULL,          -- function | method | class | field | module | window
    symbol      TEXT,                   -- qualified_name (même clé que le graphe Neo4j)
    language    TEXT NOT NULL,
    start_line  INTEGER NOT NULL,
    end_line    INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector({dim}) NOT NULL
);

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS commit_sha TEXT;

CREATE INDEX IF NOT EXISTS chunks_repo_idx ON chunks(repo_id);
CREATE INDEX IF NOT EXISTS chunks_symbol_idx ON chunks(repo_id, symbol);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS projects (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    git_url     TEXT,
    source_type TEXT NOT NULL DEFAULT 'git',
    status      TEXT NOT NULL DEFAULT 'created'
                CHECK (status IN ('created', 'pending', 'indexing', 'ready', 'failed')),
    commit_sha  TEXT,
    error       TEXT,
    languages   JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    technologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    project_type TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS technologies JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_type TEXT;

CREATE TABLE IF NOT EXISTS commits (
    id           BIGSERIAL PRIMARY KEY,
    repo_name    TEXT NOT NULL,
    sha          TEXT NOT NULL,
    message      TEXT,
    author       TEXT,
    committed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo_name, sha)
);

CREATE TABLE IF NOT EXISTS issues (
    id          BIGSERIAL PRIMARY KEY,
    repo_name   TEXT NOT NULL,
    external_id TEXT,
    title       TEXT NOT NULL,
    description TEXT,
    kind        TEXT NOT NULL DEFAULT 'unknown',
    status      TEXT NOT NULL DEFAULT 'open',
    labels      JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo_name, external_id)
);

CREATE INDEX IF NOT EXISTS issues_repo_idx ON issues(repo_name);

CREATE TABLE IF NOT EXISTS documents (
    id         BIGSERIAL PRIMARY KEY,
    repo_name  TEXT NOT NULL,
    path       TEXT NOT NULL,
    title      TEXT,
    kind       TEXT NOT NULL DEFAULT 'markdown',
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repo_name, path)
);

CREATE INDEX IF NOT EXISTS documents_repo_idx ON documents(repo_name);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id          BIGSERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
    source_type TEXT NOT NULL,
    files       INTEGER NOT NULL DEFAULT 0,
    chunks      INTEGER NOT NULL DEFAULT 0,
    symbols     INTEGER NOT NULL DEFAULT 0,
    commit_sha  TEXT,
    error       TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ingestion_runs_project_idx
    ON ingestion_runs(project_id, started_at DESC);

CREATE TABLE IF NOT EXISTS model_predictions (
    id            BIGSERIAL PRIMARY KEY,
    repo_name     TEXT NOT NULL,
    model_name    TEXT NOT NULL,
    model_version TEXT,
    target_type   TEXT NOT NULL,
    target_id     TEXT,
    file          TEXT,
    symbol        TEXT,
    label         TEXT,
    score         DOUBLE PRECISION,
    payload       JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_predictions_repo_idx
    ON model_predictions(repo_name, model_name, created_at DESC);

CREATE TABLE IF NOT EXISTS rag_queries (
    id         BIGSERIAL PRIMARY KEY,
    repo_name  TEXT NOT NULL,
    question   TEXT NOT NULL,
    answer     TEXT,
    top_k      INTEGER,
    latency_ms INTEGER,
    citations  INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_queries_repo_idx
    ON rag_queries(repo_name, created_at DESC);

CREATE TABLE IF NOT EXISTS rag_feedback (
    id         BIGSERIAL PRIMARY KEY,
    query_id   BIGINT NOT NULL REFERENCES rag_queries(id) ON DELETE CASCADE,
    rating     INTEGER NOT NULL,
    comment    TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS monitoring_metrics (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    value      DOUBLE PRECISION NOT NULL,
    labels     JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS monitoring_metrics_name_idx
    ON monitoring_metrics(name, created_at DESC);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def ensure_schema(dim: int | None = None, dsn: str | None = None) -> None:
    with psycopg.connect(dsn or settings.postgres_dsn) as conn:
        conn.execute(schema_sql(dim or settings.embedding_dim))
