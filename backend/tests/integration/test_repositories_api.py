from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_rejects_non_https_url():
    r = client.post("/api/v1/repositories/analyze", json={"git_url": "file:///etc"})
    assert r.status_code == 400
