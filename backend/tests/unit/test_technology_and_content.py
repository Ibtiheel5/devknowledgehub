import json
from pathlib import Path

from app.code_intelligence.symbol_extractor import analyze_directory
from app.code_intelligence.technology_detector import detect_technologies
from app.services.content_service import (
    classify_issue,
    collect_documents,
    extract_mentions,
)


def test_detect_full_stack_technologies(tmp_path: Path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19.0.0", "axios": "^1.7.0"},
                "devDependencies": {"vite": "^6.0.0", "typescript": "^5.6.0"},
            }
        )
    )
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "requirements.txt").write_text(
        "fastapi==0.115\nneo4j==5.24\npsycopg[binary]==3.2\n"
    )
    (tmp_path / "backend" / "app.py").write_text("from fastapi import FastAPI\n")
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  db:\n    image: pgvector/pgvector:pg16\n  graph:\n"
        "    image: neo4j:5\n"
    )
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    analysis = analyze_directory(tmp_path)
    tech = detect_technologies(tmp_path, analysis)
    names = {t["name"] for t in tech["technologies"]}

    assert {"Python", "React", "FastAPI", "PostgreSQL", "pgvector", "Neo4j"} <= names
    assert tech["project_type"] == "full-stack"
    assert "React" in tech["frameworks"]


def test_collect_documents_and_mentions(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "auth.md").write_text(
        "# Authentication\n\nThe `AuthService.login` method calls `src/auth.py`.\n"
    )
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.md").write_text("# no\n")

    docs = collect_documents(tmp_path)
    paths = {d["path"] for d in docs}
    assert paths == {"docs/auth.md", "README.md"}
    assert next(d for d in docs if d["path"] == "docs/auth.md")["title"] == "Authentication"

    files, symbols = extract_mentions(
        docs[0]["content"] if docs[0]["path"] == "docs/auth.md" else docs[1]["content"],
        ["src/auth.py", "src/other.py"],
        ["AuthService.login", "AuthService.logout"],
    )
    assert files == ["src/auth.py"]
    assert symbols == ["AuthService.login"]


def test_classify_issue():
    assert classify_issue("Crash when login with null user") == "BUG"
    assert classify_issue("Add support for SSO providers") == "FEATURE"
    assert classify_issue("Refactor auth module to reduce complexity") == "TECHNICAL_DEBT"
    assert classify_issue("Question about the roadmap") == "UNKNOWN"


def test_transformer_labels_are_normalized():
    from app.services.content_service import _normalize_model_label

    assert _normalize_model_label("BUG") == "BUG"
    assert _normalize_model_label("FEATURE") == "FEATURE"
    assert _normalize_model_label("TECH DEBT") == "TECHNICAL_DEBT"
    assert _normalize_model_label("DOCUMENTATION") == "UNKNOWN"
