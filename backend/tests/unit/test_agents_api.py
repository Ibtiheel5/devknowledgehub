from fastapi.testclient import TestClient

from app.api.v1 import agents
from app.main import app
from app.schemas.agents import Evidence, SearchResponse, ToolCall

client = TestClient(app)


def test_catalog_endpoint_lists_all_agents():
    response = client.get("/api/v1/agents/catalog")

    assert response.status_code == 200
    body = response.json()
    assert len(body["agents"]) == 8
    assert {agent["name"] for agent in body["agents"]} >= {
        "architecture",
        "impact",
        "triage",
        "review",
        "test_plan",
    }


def test_specialist_endpoint_rejects_unknown_agent():
    response = client.post(
        "/api/v1/agents/specialist",
        json={"repo_name": "demo", "agent": "unknown", "question": "Explique le projet."},
    )

    assert response.status_code == 400
    assert "Agent inconnu" in response.json()["detail"]


def test_specialist_endpoint_records_agent_name(monkeypatch):
    recorded = []

    class FakeRunStore:
        def ensure_schema(self):
            return None

        def record(self, **kwargs):
            recorded.append(kwargs)

    def fake_run_agent(agent_name, repo_name, question, **kwargs):
        return SearchResponse(
            agent=agent_name,
            intent="architecture",
            question=question,
            answer="Architecture observée [S1].",
            model="test-model",
            terms=["architecture"],
            evidence=[
                Evidence(
                    id="S1",
                    qualified_name="app.main",
                    kind="file",
                    file="app/main.py",
                    reason="point d'entrée",
                    source="rag",
                )
            ],
            trace=[ToolCall(tool="rag_search", args={"top_k": 5}, n_results=1)],
        )

    monkeypatch.setattr(agents, "AgentRunStore", FakeRunStore)
    monkeypatch.setattr(agents, "OllamaChatClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(agents, "GraphTools", lambda *args, **kwargs: object())
    monkeypatch.setattr(agents, "Retriever", lambda *args, **kwargs: object())
    monkeypatch.setattr(agents, "ChunkStore", lambda: object())
    monkeypatch.setattr(agents, "get_embedder", lambda: object())
    monkeypatch.setattr(agents, "get_driver", lambda: object())
    monkeypatch.setattr(agents, "run_agent", fake_run_agent)

    response = client.post(
        "/api/v1/agents/specialist",
        json={
            "repo_name": "demo",
            "agent": "architecture",
            "question": "Décris l'architecture du projet.",
            "max_results": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "architecture"
    assert recorded[0]["agent"] == "architecture"
    assert recorded[0]["status"] == "success"
    assert recorded[0]["citations"] == 1
