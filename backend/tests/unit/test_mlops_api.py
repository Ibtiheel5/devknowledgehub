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
