from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.v1 import mlops
from app.main import app

client = TestClient(app)


def test_agent_runs_endpoint_returns_summary_and_recent_runs(monkeypatch):
    class FakeStore:
        initialized = False

        def ensure_schema(self):
            self.initialized = True

        def summary(self):
            return {
                "total": 1,
                "successful": 1,
                "failed": 0,
                "avg_duration_ms": 1400,
                "latest_model": "qwen2.5-coder:1.5b",
            }

        def recent(self, limit):
            assert limit == 10
            return [
                {
                    "id": 1,
                    "repo_name": "demo",
                    "model": "qwen2.5-coder:1.5b",
                    "status": "success",
                    "duration_ms": 1400,
                    "retrieved_chunks": 3,
                    "graph_evidence": 1,
                    "citations": 4,
                    "created_at": datetime(2026, 10, 28, tzinfo=UTC),
                }
            ]

    fake_store = FakeStore()
    monkeypatch.setattr(mlops, "AgentRunStore", lambda: fake_store)

    response = client.get("/api/v1/mlops/agent-runs?limit=10")

    assert response.status_code == 200
    assert fake_store.initialized
    assert response.json()["summary"]["successful"] == 1
    assert response.json()["runs"][0]["model"] == "qwen2.5-coder:1.5b"


def test_agent_runs_endpoint_validates_limit():
    response = client.get("/api/v1/mlops/agent-runs?limit=500")

    assert response.status_code == 422


def test_monitoring_endpoint_returns_overview(monkeypatch):
    class FakeMonitoringStore:
        def ensure_schema(self):
            return None

        def overview(self, repo_name=None, days=7):
            return {
                "repo_name": repo_name,
                "window_days": days,
                "agents": {"total": 2, "success_rate": 0.5},
                "rag": {"total": 3, "avg_latency_ms": 900},
            }

    monkeypatch.setattr(mlops, "MonitoringStore", FakeMonitoringStore)
    response = client.get("/api/v1/mlops/monitoring?repo_name=demo&days=30")

    assert response.status_code == 200
    body = response.json()
    assert body["repo_name"] == "demo"
    assert body["window_days"] == 30
    assert body["agents"]["success_rate"] == 0.5


def test_record_metric_endpoint(monkeypatch):
    recorded = []

    class FakeMonitoringStore:
        def ensure_schema(self):
            return None

        def record_metric(self, name, value, labels=None):
            recorded.append((name, value, labels))

    monkeypatch.setattr(mlops, "MonitoringStore", FakeMonitoringStore)
    response = client.post(
        "/api/v1/mlops/metrics",
        json={"name": "rag_latency_ms", "value": 123.4, "labels": {"repo": "demo"}},
    )

    assert response.status_code == 201
    assert recorded == [("rag_latency_ms", 123.4, {"repo": "demo"})]
