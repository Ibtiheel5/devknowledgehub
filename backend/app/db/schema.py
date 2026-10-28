"""Schéma Postgres du RAG. Idempotent : peut être rejoué à chaque démarrage."""
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

CREATE TABLE IF NOT EXISTS chunks (
    id          BIGSERIAL PRIMARY KEY,
    repo_id     INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file        TEXT NOT NULL,
    kind        TEXT NOT NULL,          -- function | method | class | module | window
    symbol      TEXT,                   -- qualified_name (même clé que le graphe Neo4j)
    language    TEXT NOT NULL,
    start_line  INTEGER NOT NULL,
    end_line    INTEGER NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector({dim}) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_repo_idx ON chunks(repo_id);
CREATE INDEX IF NOT EXISTS chunks_symbol_idx ON chunks(repo_id, symbol);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
"""


def ensure_schema(dim: int | None = None, dsn: str | None = None) -> None:
    with psycopg.connect(dsn or settings.postgres_dsn) as conn:
        conn.execute(schema_sql(dim or settings.embedding_dim))
