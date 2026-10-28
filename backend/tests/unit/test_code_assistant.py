from types import SimpleNamespace

from app.agents.code_assistant import CodeAssistantAgent


class FakeRetriever:
    def __init__(self):
        self.top_k = None

    def search(self, repo_name, question, top_k):
        self.top_k = top_k
        return SimpleNamespace(
            hits=[
                SimpleNamespace(
                    file="src/auth.py",
                    start_line=10,
                    end_line=15,
                    symbol="Auth.refresh",
                    kind="method",
                    snippet="def refresh():\n    return token",
                )
            ]
        )


class FakeGraphTools:
    def search_symbols(self, term):
        if term.lower() in {"auth", "refresh", "auth.refresh"}:
            return [
                {
                    "qualified_name": "Auth.refresh",
                    "name": "refresh",
                    "kind": "method",
                    "file": "src/auth.py",
                    "start_line": 10,
                    "end_line": 15,
                }
            ]
        return []

    def callers(self, qualified_name):
        return []

    def callees(self, qualified_name):
        return []

    def overview(self):
        return {"stats": {}, "symbols": [], "files": [], "modules": []}


class FakeLlm:
    model = "test-model"

    def __init__(self):
        self.user_prompt = ""
        self.system_prompt = ""

    def chat(self, system_prompt, user_prompt):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return "La méthode retourne le token [S1]."


def test_agent_uses_code_and_graph_context_and_returns_citations():
    llm = FakeLlm()
    retriever = FakeRetriever()
    agent = CodeAssistantAgent("demo", FakeGraphTools(), retriever, llm)

    response = agent.run("Comment fonctionne Auth.refresh ?")

    assert response.answer == "La méthode retourne le token [S1]."
    assert response.model == "test-model"
    assert response.citations[0].id == "S1"
    assert response.citations[0].file == "src/auth.py"
    assert "def refresh()" in llm.user_prompt
    assert "Symbole Auth.refresh" in llm.user_prompt
    assert "N’invente aucune fonctionnalité" in llm.system_prompt
    assert retriever.top_k == 5
    assert any(step.tool == "rag_search" for step in response.trace)
    assert any(step.tool == "search_symbols" for step in response.trace)


def test_agent_limits_fallback_sources_when_model_omits_citations():
    class NoCitationLlm(FakeLlm):
        def chat(self, system_prompt, user_prompt):
            return "Voici une réponse structurée."

    llm = NoCitationLlm()
    agent = CodeAssistantAgent("demo", FakeGraphTools(), FakeRetriever(), llm)

    response = agent.run("Comment fonctionne Auth.refresh ?")

    assert response.answer.endswith("Éléments consultés : [S1], [S2]")
    assert [citation.id for citation in response.citations] == ["S1", "S2"]


def test_agent_answers_project_name_without_rag_or_llm():
    class UnusedRetriever:
        def search(self, *args, **kwargs):
            raise AssertionError("Project name should not trigger retrieval")

    llm = FakeLlm()
    agent = CodeAssistantAgent("calorie_IA", FakeGraphTools(), UnusedRetriever(), llm)

    response = agent.run("cest quoi le nom de ce projet !")

    assert response.answer == "Le nom du projet actif est **calorie_IA**."
    assert response.citations == []
    assert response.model is None
    assert response.trace[0].tool == "project_name"
    assert llm.user_prompt == ""


def test_agent_does_not_call_llm_without_any_context():
    class EmptyRetriever:
        def search(self, repo_name, question, top_k):
            return SimpleNamespace(hits=[])

    class EmptyGraphTools(FakeGraphTools):
        def search_symbols(self, term):
            return []

        def overview(self):
            return {"stats": {}, "symbols": [], "files": [], "modules": []}

    llm = FakeLlm()
    response = CodeAssistantAgent("empty", EmptyGraphTools(), EmptyRetriever(), llm).run(
        "Where is the cache?"
    )

    assert "aucune source" in response.answer
    assert response.citations == []
    assert response.model is None
    assert llm.user_prompt == ""
