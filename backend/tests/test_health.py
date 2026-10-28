from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from app.api.v1 import health
from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_dependency_status(monkeypatch):
    monkeypatch.setattr(health, "_check_postgres", lambda: True)
    monkeypatch.setattr(health, "_check_neo4j", lambda: False)

    r = client.get("/health")

    assert r.status_code == 200
    assert r.json() == {"api": "ok", "postgres": True, "neo4j": False}


def test_neo4j_check_handles_service_unavailable(monkeypatch):
    class UnavailableDriver:
        def verify_connectivity(self):
            raise ServiceUnavailable("Neo4j is unavailable")

    monkeypatch.setattr(health.GraphDatabase, "driver", lambda *args, **kwargs: UnavailableDriver())

    assert health._check_neo4j() is False
