"""Persistance des projets, runs d'ingestion, tickets et findings (Postgres)."""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.db.schema import ensure_schema


class ProjectStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or settings.postgres_dsn

    def ensure_schema(self) -> None:
        ensure_schema(dsn=self.dsn)

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def create(
        self, name: str, git_url: str | None = None, source_type: str = "git"
    ) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO projects (name, git_url, source_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                    SET git_url = COALESCE(EXCLUDED.git_url, projects.git_url),
                        source_type = EXCLUDED.source_type,
                        updated_at = now()
                RETURNING *
                """,
                (name, git_url, source_type),
            ).fetchone()
        return row

    def get(self, name: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM projects WHERE name = %s", (name,)
            ).fetchone()

    def list_projects(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC, id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return rows

    def set_status(
        self,
        name: str,
        status: str,
        *,
        error: str | None = None,
        commit_sha: str | None = None,
        languages: dict | None = None,
        technologies: list | None = None,
        project_type: str | None = None,
    ) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                """
                UPDATE projects
                SET status = %s,
                    error = %s,
                    commit_sha = COALESCE(%s, commit_sha),
                    languages = COALESCE(%s, languages),
                    technologies = COALESCE(%s, technologies),
                    project_type = COALESCE(%s, project_type),
                    updated_at = now()
                WHERE name = %s
                RETURNING *
                """,
                (
                    status,
                    error,
                    commit_sha,
                    Jsonb(languages) if languages is not None else None,
                    Jsonb(technologies) if technologies is not None else None,
                    project_type,
                    name,
                ),
            ).fetchone()

    def create_run(self, project_id: int, source_type: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO ingestion_runs (project_id, status, source_type)
                VALUES (%s, 'pending', %s)
                RETURNING id
                """,
                (project_id, source_type),
            ).fetchone()
        return row["id"]

    def start_run(self, run_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE ingestion_runs SET status = 'running', started_at = now() "
                "WHERE id = %s",
                (run_id,),
            )

    def finish_run(
        self,
        run_id: int,
        status: str,
        *,
        files: int = 0,
        chunks: int = 0,
        symbols: int = 0,
        commit_sha: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET status = %s, files = %s, chunks = %s, symbols = %s,
                    commit_sha = %s, error = %s, finished_at = now()
                WHERE id = %s
                """,
                (status, files, chunks, symbols, commit_sha, error, run_id),
            )

    def latest_run(self, project_name: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT r.*
                FROM ingestion_runs r
                JOIN projects p ON p.id = r.project_id
                WHERE p.name = %s
                ORDER BY r.started_at DESC, r.id DESC
                LIMIT 1
                """,
                (project_name,),
            ).fetchone()

    def list_runs(self, project_name: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.*
                FROM ingestion_runs r
                JOIN projects p ON p.id = r.project_id
                WHERE p.name = %s
                ORDER BY r.started_at DESC, r.id DESC
                LIMIT %s
                """,
                (project_name, limit),
            ).fetchall()
        return rows

    def upsert_commit(
        self,
        repo_name: str,
        sha: str,
        *,
        message: str | None = None,
        author: str | None = None,
        committed_at=None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO commits (repo_name, sha, message, author, committed_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (repo_name, sha) DO UPDATE
                    SET message = EXCLUDED.message,
                        author = EXCLUDED.author,
                        committed_at = EXCLUDED.committed_at
                """,
                (repo_name, sha, message, author, committed_at),
            )

    def upsert_document(
        self,
        repo_name: str,
        path: str,
        *,
        title: str | None,
        kind: str,
        content: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (repo_name, path, title, kind, content)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (repo_name, path) DO UPDATE
                    SET title = EXCLUDED.title,
                        kind = EXCLUDED.kind,
                        content = EXCLUDED.content
                """,
                (repo_name, path, title, kind, content),
            )

    def list_documents(
        self, repo_name: str, limit: int = 200, include_content: bool = False
    ) -> list[dict]:
        columns = "*" if include_content else "id, repo_name, path, title, kind, created_at"
        with self._connect() as conn:
            return conn.execute(
                f"SELECT {columns} FROM documents WHERE repo_name = %s "
                "ORDER BY path LIMIT %s",
                (repo_name, limit),
            ).fetchall()

    def get_document(self, repo_name: str, path: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM documents WHERE repo_name = %s AND path = %s",
                (repo_name, path),
            ).fetchone()

    def add_issue(
        self,
        repo_name: str,
        title: str,
        *,
        description: str | None = None,
        kind: str = "unknown",
        status: str = "open",
        external_id: str | None = None,
        labels: list[str] | None = None,
    ) -> dict:
        with self._connect() as conn:
            return conn.execute(
                """
                INSERT INTO issues
                    (repo_name, external_id, title, description, kind, status, labels)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (repo_name, external_id) DO UPDATE
                    SET title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        kind = EXCLUDED.kind,
                        status = EXCLUDED.status,
                        labels = EXCLUDED.labels
                RETURNING *
                """,
                (
                    repo_name,
                    external_id,
                    title,
                    description,
                    kind,
                    status,
                    Jsonb(labels or []),
                ),
            ).fetchone()

    def list_issues(self, repo_name: str, limit: int = 200) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM issues WHERE repo_name = %s "
                "ORDER BY created_at DESC, id DESC LIMIT %s",
                (repo_name, limit),
            ).fetchall()

    def list_findings(
        self, repo_name: str, limit: int = 100, model_name: str | None = None
    ) -> list[dict]:
        query = (
            "SELECT * FROM model_predictions WHERE repo_name = %s "
            "AND (%s::text IS NULL OR model_name = %s) "
            "ORDER BY created_at DESC, id DESC LIMIT %s"
        )
        with self._connect() as conn:
            rows = conn.execute(
                query, (repo_name, model_name, model_name, limit)
            ).fetchall()
        return rows

    def add_predictions(self, repo_name: str, predictions: list[dict]) -> int:
        if not predictions:
            return 0
        rows = [
            (
                repo_name,
                item.get("model_name") or "unknown",
                item.get("model_version"),
                item.get("target_type") or "file",
                item.get("target_id"),
                item.get("file"),
                item.get("symbol"),
                item.get("label"),
                item.get("score"),
                Jsonb(item.get("payload") or {}),
            )
            for item in predictions
        ]
        with self._connect() as conn, conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO model_predictions
                    (repo_name, model_name, model_version, target_type,
                     target_id, file, symbol, label, score, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
        return len(rows)

    def clear_predictions(self, repo_name: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM model_predictions WHERE repo_name = %s", (repo_name,))

    def record_rag_query(
        self,
        repo_name: str,
        question: str,
        *,
        answer: str | None = None,
        top_k: int | None = None,
        latency_ms: int | None = None,
        citations: int = 0,
    ) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO rag_queries
                    (repo_name, question, answer, top_k, latency_ms, citations)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (repo_name, question, answer, top_k, latency_ms, citations),
            ).fetchone()
        return row["id"]

    def add_feedback(self, query_id: int, rating: int, comment: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rag_feedback (query_id, rating, comment) VALUES (%s, %s, %s)",
                (query_id, rating, comment),
            )

    def recent_queries(self, repo_name: str | None = None, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM rag_queries
                WHERE (%s::text IS NULL OR repo_name = %s)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (repo_name, repo_name, limit),
            ).fetchall()
        return rows
