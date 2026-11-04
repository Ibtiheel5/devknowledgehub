"""Agrégats de monitoring et qualité pour le tableau de bord MLOps."""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.db.schema import ensure_schema


class MonitoringStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or settings.postgres_dsn

    def ensure_schema(self) -> None:
        ensure_schema(dsn=self.dsn)

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def record_metric(self, name: str, value: float, labels: dict | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO monitoring_metrics (name, value, labels) VALUES (%s, %s, %s)",
                (name, value, Jsonb(labels or {})),
            )

    def list_metrics(self, name: str | None = None, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM monitoring_metrics "
                "WHERE (%s::text IS NULL OR name = %s) "
                "ORDER BY created_at DESC, id DESC LIMIT %s",
                (name, name, limit),
            ).fetchall()

    def overview(self, repo_name: str | None = None, days: int = 7) -> dict:
        with self._connect() as conn:
            agents = conn.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE status = 'success') AS successful,
                       count(*) FILTER (WHERE status = 'failed') AS failed,
                       coalesce(round(avg(duration_ms))::integer, 0) AS avg_duration_ms,
                       coalesce(round(percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms))::integer, 0)
                           AS p95_duration_ms
                FROM agent_runs
                WHERE created_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR repo_name = %s)
                """,
                (days, repo_name, repo_name),
            ).fetchone()

            rag = conn.execute(
                """
                SELECT count(*) AS total,
                       coalesce(round(avg(latency_ms))::integer, 0) AS avg_latency_ms,
                       coalesce(round(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms))::integer, 0)
                           AS p95_latency_ms,
                       coalesce(sum(citations), 0) AS citations
                FROM rag_queries
                WHERE created_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR repo_name = %s)
                """,
                (days, repo_name, repo_name),
            ).fetchone()

            feedback = conn.execute(
                """
                SELECT count(*) AS total, coalesce(round(avg(f.rating)::numeric, 2), 0) AS avg_rating
                FROM rag_feedback f
                JOIN rag_queries q ON q.id = f.query_id
                WHERE f.created_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR q.repo_name = %s)
                """,
                (days, repo_name, repo_name),
            ).fetchone()

            predictions = conn.execute(
                """
                SELECT count(*) AS total,
                       count(DISTINCT file) AS files_with_findings,
                       coalesce(round(avg(score)::numeric, 4), 0) AS avg_score
                FROM model_predictions
                WHERE created_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR repo_name = %s)
                """,
                (days, repo_name, repo_name),
            ).fetchone()

            by_model = conn.execute(
                """
                SELECT model_name, count(*) AS findings,
                       coalesce(round(avg(score)::numeric, 4), 0) AS avg_score
                FROM model_predictions
                WHERE created_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR repo_name = %s)
                GROUP BY model_name
                ORDER BY findings DESC
                """,
                (days, repo_name, repo_name),
            ).fetchall()

            ingestion = conn.execute(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE r.status = 'succeeded') AS succeeded,
                       count(*) FILTER (WHERE r.status = 'failed') AS failed,
                       coalesce(round(avg(extract(epoch FROM (r.finished_at - r.started_at))))::integer, 0)
                           AS avg_duration_seconds
                FROM ingestion_runs r
                JOIN projects p ON p.id = r.project_id
                WHERE r.started_at >= now() - make_interval(days => %s)
                  AND (%s::text IS NULL OR p.name = %s)
                """,
                (days, repo_name, repo_name),
            ).fetchone()

        agent_total = agents["total"] or 0
        return {
            "repo_name": repo_name,
            "window_days": days,
            "agents": {
                **agents,
                "success_rate": round(agents["successful"] / agent_total, 4) if agent_total else 0.0,
            },
            "rag": rag,
            "feedback": feedback,
            "predictions": predictions,
            "predictions_by_model": by_model,
            "ingestion": ingestion,
        }

    def models(self, repo_name: str | None = None) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT model_name, model_version, count(*) AS predictions,
                       count(DISTINCT repo_name) AS repositories,
                       count(DISTINCT file) AS files,
                       coalesce(round(avg(score)::numeric, 4), 0) AS avg_score,
                       max(created_at) AS last_seen
                FROM model_predictions
                WHERE (%s::text IS NULL OR repo_name = %s)
                GROUP BY model_name, model_version
                ORDER BY predictions DESC
                """,
                (repo_name, repo_name),
            ).fetchall()

    def quality(self, repo_name: str | None = None, model_name: str | None = None) -> dict:
        with self._connect() as conn:
            by_label = conn.execute(
                """
                SELECT model_name, label, count(*) AS findings,
                       coalesce(round(avg(score)::numeric, 4), 0) AS avg_score
                FROM model_predictions
                WHERE (%s::text IS NULL OR repo_name = %s)
                  AND (%s::text IS NULL OR model_name = %s)
                GROUP BY model_name, label
                ORDER BY findings DESC
                """,
                (repo_name, repo_name, model_name, model_name),
            ).fetchall()

            feedback = conn.execute(
                """
                SELECT count(*) AS total,
                       coalesce(round(avg(rating)::numeric, 2), 0) AS avg_rating,
                       count(*) FILTER (WHERE rating >= 4) AS positive,
                       count(*) FILTER (WHERE rating <= 2) AS negative
                FROM rag_feedback f
                JOIN rag_queries q ON q.id = f.query_id
                WHERE (%s::text IS NULL OR q.repo_name = %s)
                """,
                (repo_name, repo_name),
            ).fetchone()

        total = feedback["total"] or 0
        return {
            "repo_name": repo_name,
            "model_name": model_name,
            "findings_by_label": by_label,
            "feedback": {
                **feedback,
                "positive_rate": round(feedback["positive"] / total, 4) if total else 0.0,
            },
        }
