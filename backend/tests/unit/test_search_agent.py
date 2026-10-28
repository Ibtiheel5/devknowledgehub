from app.agents.search_agent import SearchAgent, extract_terms, is_overview_question
from app.schemas.rag import RagHit, RagSearchResponse


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


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def search(self, repo_name, question, top_k):
        self.calls.append((repo_name, question, top_k))
        return RagSearchResponse(
            question=question,
            terms=[],
            hits=[
                RagHit(
                    file="docs/authentication.md",
                    kind="document",
                    symbol=None,
                    start_line=4,
                    end_line=12,
                    score=0.82,
                    vector_score=0.78,
                    snippet="Authentication flow and token refresh.",
                )
            ],
        )


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


def test_agent_searches_rag_and_returns_citable_document_evidence():
    retriever = FakeRetriever()
    response = SearchAgent(
        FakeTools(), retriever=retriever, repo_name="demo"
    ).run("Where can I read about authentication?", max_results=4)

    assert retriever.calls == [("demo", "Where can I read about authentication?", 4)]
    assert response.evidence[0].qualified_name == "docs/authentication.md"
    assert response.evidence[0].source == "rag"
    assert response.evidence[0].citation == "docs/authentication.md:4-12"
    assert response.evidence[0].snippet == "Authentication flow and token refresh."
    assert response.trace[0].tool == "rag_search"
    assert not any(step.tool in {"callers", "callees"} for step in response.trace)


def test_overview_search_includes_rag_results():
    response = SearchAgent(
        FakeTools(), retriever=FakeRetriever(), repo_name="demo"
    ).run("Que fait ce projet ?")

    assert response.intent == "overview"
    assert any(e.source == "rag" for e in response.evidence)
    assert any(step.tool == "rag_search" for step in response.trace)


def test_agent_keeps_rag_snippet_when_graph_finds_same_symbol():
    class MatchingRetriever(FakeRetriever):
        def search(self, repo_name, question, top_k):
            return RagSearchResponse(
                question=question,
                terms=["AuthService"],
                hits=[
                    RagHit(
                        file="backend/services/auth.py",
                        kind="class",
                        symbol="AuthService",
                        start_line=10,
                        end_line=200,
                        score=0.82,
                        vector_score=0.78,
                        snippet="class AuthService: ...",
                    )
                ],
            )

    response = SearchAgent(
        FakeTools(), retriever=MatchingRetriever(), repo_name="demo"
    ).run("AuthService")
    evidence = next(item for item in response.evidence if item.qualified_name == "AuthService")

    assert evidence.source == "rag"
    assert evidence.snippet == "class AuthService: ..."
    assert "confirmé par le graphe" in evidence.reason
