import psycopg

from app.config import settings


class AgentRunStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or settings.postgres_dsn

    def ensure_schema(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id BIGSERIAL PRIMARY KEY,
                    repo_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
                    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
                    retrieved_chunks INTEGER NOT NULL DEFAULT 0,
                    graph_evidence INTEGER NOT NULL DEFAULT 0,
                    citations INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS agent TEXT NOT NULL "
                "DEFAULT 'copilot'"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS agent_runs_created_at_idx "
                "ON agent_runs(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS agent_runs_agent_idx "
                "ON agent_runs(agent, created_at DESC)"
            )

    def record(
        self,
        *,
        repo_name: str,
        model: str,
        status: str,
        duration_ms: int,
        agent: str = "copilot",
        retrieved_chunks: int = 0,
        graph_evidence: int = 0,
        citations: int = 0,
    ) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO agent_runs (
                    repo_name, agent, model, status, duration_ms,
                    retrieved_chunks, graph_evidence, citations
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    repo_name,
                    agent,
                    model,
                    status,
                    duration_ms,
                    retrieved_chunks,
                    graph_evidence,
                    citations,
                ),
            )

    def summary(self) -> dict:
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE status = 'success') AS successful,
                       count(*) FILTER (WHERE status = 'failed') AS failed,
                       coalesce(round(avg(duration_ms))::integer, 0) AS avg_duration_ms,
                       (array_agg(model ORDER BY created_at DESC))[1] AS latest_model,
                       (array_agg(agent ORDER BY created_at DESC))[1] AS latest_agent
                FROM agent_runs
                """
            ).fetchone()
            by_agent = conn.execute(
                """
                SELECT agent, count(*) AS total,
                       count(*) FILTER (WHERE status = 'success') AS successful,
                       coalesce(round(avg(duration_ms))::integer, 0) AS avg_duration_ms
                FROM agent_runs
                GROUP BY agent
                ORDER BY total DESC, agent
                """
            ).fetchall()
        return {
            "total": row[0],
            "successful": row[1],
            "failed": row[2],
            "avg_duration_ms": row[3],
            "latest_model": row[4],
            "latest_agent": row[5],
            "by_agent": [
                {
                    "agent": item[0],
                    "total": item[1],
                    "successful": item[2],
                    "avg_duration_ms": item[3],
                }
                for item in by_agent
            ],
        }

    def recent(self, limit: int = 50) -> list[dict]:
        with psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                """
                SELECT id, repo_name, agent, model, status, duration_ms,
                       retrieved_chunks, graph_evidence, citations, created_at
                FROM agent_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        keys = (
            "id", "repo_name", "agent", "model", "status", "duration_ms",
            "retrieved_chunks", "graph_evidence", "citations", "created_at",
        )
        return [dict(zip(keys, row)) for row in rows]
