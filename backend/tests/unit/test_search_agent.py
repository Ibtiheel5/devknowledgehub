from app.agents.search_agent import SearchAgent, extract_terms, is_overview_question


class FakeTools:
    def __init__(self):
        self.symbols = {
            "refresh_token": [
                {"qualified_name": "AuthService.refresh_token", "name": "refresh_token",
                 "kind": "method", "file": "backend/services/auth.py",
                 "start_line": 90, "end_line": 120}
            ],
            "AuthService": [
                {"qualified_name": "AuthService", "name": "AuthService", "kind": "class",
                 "file": "backend/services/auth.py", "start_line": 10, "end_line": 200},
                {"qualified_name": "AuthService.refresh_token", "name": "refresh_token",
                 "kind": "method", "file": "backend/services/auth.py",
                 "start_line": 90, "end_line": 120},
            ],
        }

    def search_symbols(self, term, limit=20):
        return self.symbols.get(term, [])

    def callers(self, qn):
        return [{"qualified_name": "AuthController.refresh", "kind": "method", "line": 14}] \
            if qn == "AuthService.refresh_token" else []

    def callees(self, qn):
        return []

    def overview(self):
        return {
            "stats": {"files": 3, "symbols": 12, "modules": 4, "imports": 6, "calls": 9},
            "symbols": [{"qualified_name": "AuthService", "kind": "class",
                         "file": "auth.py", "start_line": 1, "end_line": 50, "degree": 7}],
            "files": [{"path": "auth.py", "language": "python", "symbols": 8}],
            "modules": [{"name": "fastapi", "files": 3}],
        }


def test_extract_terms_prioritizes_code_identifiers():
    terms = extract_terms("Pourquoi AuthService.refresh_token échoue après l'expiration ?")
    assert terms[0] in {"AuthService.refresh_token", "refresh_token", "AuthService"}
    assert "Pourquoi" not in terms


def test_extract_terms_ignores_stopwords():
    assert extract_terms("why does the it fail") == []


def test_agent_returns_cited_evidence_and_expands_graph():
    res = SearchAgent(FakeTools()).run("bug dans AuthService et refresh_token")
    names = [e.qualified_name for e in res.evidence]
    assert names[0] == "AuthService.refresh_token" or names[0] == "AuthService"
    assert "AuthController.refresh" in names          # trouvé via le graphe
    top = next(e for e in res.evidence if e.qualified_name == "AuthService.refresh_token")
    assert top.citation == "backend/services/auth.py:90-120"
    assert any(t.tool == "callers" for t in res.trace)


def test_agent_with_no_terms_returns_empty():
    res = SearchAgent(FakeTools()).run("why does it fail")
    assert res.evidence == [] and res.trace == []


def test_general_question_gives_project_overview():
    assert is_overview_question("que fait ce projet !")
    assert is_overview_question("What does this project do?")
    res = SearchAgent(FakeTools()).run("que fait ce projet !")
    assert res.intent == "overview" and res.overview.stats["files"] == 3
    assert res.overview.top_modules[0]["name"] == "fastapi"


def test_generic_words_are_not_search_terms():
    assert extract_terms("que fait ce projet") == []
