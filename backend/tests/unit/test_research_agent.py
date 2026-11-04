from app.agents.research_agent import ResearchAgent
from app.schemas.rag import RagHit, RagSearchResponse


class FakeGraphTools:
    def __init__(self):
        self.symbol_searches = []
        self.caller_searches = []

    def search_symbols(self, term):
        self.symbol_searches.append(term)
        if term == "AuthService":
            return [
                {
                    "qualified_name": "AuthService.login",
                    "name": "login",
                    "kind": "method",
                    "file": "src/auth.py",
                    "start_line": 20,
                    "end_line": 32,
                }
            ]
        return []

    def callers(self, symbol):
        self.caller_searches.append(symbol)
        return [{"qualified_name": "AuthController.login", "kind": "method"}]

    def callees(self, symbol):
        return []

    def overview(self):
        return {"stats": {}, "symbols": [], "files": [], "modules": []}


class FakeRetriever:
    def search(self, repo_name, question, top_k):
        return RagSearchResponse(
            question=question,
            terms=[],
            hits=[
                RagHit(
                    file="docs/auth.md",
                    kind="document",
                    symbol=None,
                    start_line=1,
                    end_line=8,
                    score=0.9,
                    vector_score=0.9,
                    snippet="Authentication design.",
                )
            ],
        )


class FakeLlm:
    model = "test-model"

    def __init__(self, plans):
        self.plans = iter(plans)
        self.calls = []

    def chat(self, system_prompt, user_prompt, num_predict=640):
        self.calls.append((system_prompt, user_prompt, num_predict))
        if "planificateur" in system_prompt:
            return next(self.plans)
        return "La méthode est documentée dans le dépôt [S1]."


def test_agent_plans_multiple_read_only_tool_calls_then_synthesizes():
    graph = FakeGraphTools()
    llm = FakeLlm(
        [
            '{"action":"search_symbols","term":"AuthService"}',
            '{"action":"callers","symbol":"AuthService.login"}',
            '{"action":"finish"}',
        ]
    )

    result = ResearchAgent("demo", graph, FakeRetriever(), llm).run(
        "Where is authentication documented?"
    )

    assert "AuthService" in graph.symbol_searches
    assert graph.caller_searches == ["AuthService.login"]
    assert result.answer == "La méthode est documentée dans le dépôt [S1]."
    assert result.model == "test-model"
    assert [item.id for item in result.evidence] == [
        f"S{index}" for index in range(1, len(result.evidence) + 1)
    ]
    assert [step.tool for step in result.trace if step.tool == "agent_decision"] == [
        "agent_decision",
        "agent_decision",
    ]
    assert any(step.tool == "callers" for step in result.trace)
    assert llm.calls[0][2] == 80


def test_agent_rejects_unregistered_or_unsafe_tool_action():
    graph = FakeGraphTools()
    llm = FakeLlm(['{"action":"execute_code","command":"whoami"}'])

    result = ResearchAgent("demo", graph, FakeRetriever(), llm).run(
        "why does it fail?"
    )

    assert graph.symbol_searches == []
    assert graph.caller_searches == []
    assert any(
        step.tool == "agent_decision" and step.args["action"] == "finish"
        for step in result.trace
    )
    assert result.answer
