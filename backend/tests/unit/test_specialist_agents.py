from app.agents.specialist_agents import (
    AGENT_CATALOG,
    ArchitectureAgent,
    DocumentationAgent,
    ImpactAgent,
    ReviewAgent,
    ScenarioPlannerAgent,
    TriageAgent,
)
from app.schemas.rag import RagHit, RagSearchResponse


class FakeGraphTools:
    def search_symbols(self, term, limit=20):
        if term.lower() in {"authservice", "authservice.login", "login"}:
            return [
                {
                    "qualified_name": "AuthService.login",
                    "name": "login",
                    "kind": "method",
                    "file": "src/auth.py",
                    "start_line": 20,
                    "end_line": 35,
                }
            ]
        return []

    def callers(self, qualified_name):
        return []

    def callees(self, qualified_name):
        return []

    def impact(self, qualified_name, depth=3):
        return [
            {
                "qualified_name": "AuthController.login",
                "kind": "method",
                "distance": 1,
            },
            {
                "qualified_name": "Api.login",
                "kind": "method",
                "distance": 2,
            },
        ]

    def overview(self):
        return {
            "stats": {"files": 4, "symbols": 12, "modules": 3, "imports": 6, "calls": 9},
            "symbols": [
                {
                    "qualified_name": "AuthService.login",
                    "kind": "method",
                    "file": "src/auth.py",
                    "start_line": 20,
                    "end_line": 35,
                    "degree": 8,
                }
            ],
            "files": [{"path": "src/auth.py", "language": "python", "symbols": 5}],
            "modules": [{"name": "fastapi", "files": 3}],
        }


class FakeRetriever:
    def search(self, repo_name, question, top_k, kinds=None):
        hits = [
            RagHit(
                file="docs/auth.md",
                kind="document",
                symbol=None,
                start_line=1,
                end_line=8,
                score=0.9,
                vector_score=0.9,
                snippet="Authentication uses a signed token.",
            ),
            RagHit(
                file="src/auth.py",
                kind="method",
                symbol="AuthService.login",
                start_line=20,
                end_line=35,
                score=0.8,
                vector_score=0.8,
                snippet="def login(user): ...",
            ),
        ]
        if kinds:
            hits = [hit for hit in hits if hit.kind in kinds]
        return RagSearchResponse(
            question=question,
            terms=["AuthService"],
            hits=hits[:top_k],
        )


class FakeLlm:
    model = "test-model"

    def __init__(self):
        self.calls = []

    def chat(self, system_prompt, user_prompt, num_predict=640):
        self.calls.append((system_prompt, user_prompt, num_predict))
        return "Réponse fondée sur les sources [S1]."


def test_catalog_exposes_eight_specialized_agents():
    assert len(AGENT_CATALOG) == 8
    assert {agent["name"] for agent in AGENT_CATALOG} == {
        "copilot",
        "researcher",
        "architecture",
        "documentation",
        "impact",
        "triage",
        "review",
        "test_plan",
    }
    assert all(agent.get("read_only", True) for agent in AGENT_CATALOG)


def test_architecture_agent_uses_overview_and_returns_citation():
    llm = FakeLlm()
    result = ArchitectureAgent("demo", FakeGraphTools(), FakeRetriever(), llm).run(
        "Décris l'architecture du projet."
    )

    assert result.intent == "architecture"
    assert result.agent == "architecture"
    assert result.overview.stats["files"] == 4
    assert result.evidence[0].id == "S1"
    assert "[S1]" in result.answer
    assert any(step.tool == "overview" for step in result.trace)
    assert result.model == "test-model"


def test_documentation_agent_keeps_documentation_sources():
    result = DocumentationAgent("demo", FakeRetriever(), FakeLlm()).run(
        "Comment fonctionne l'authentification ?"
    )

    assert result.intent == "documentation"
    assert len(result.evidence) == 1
    assert result.evidence[0].file == "docs/auth.md"
    assert result.evidence[0].source == "rag"
    assert result.answer


def test_impact_agent_finds_transitive_callers():
    result = ImpactAgent("demo", FakeGraphTools(), FakeRetriever(), FakeLlm()).run(
        "Quel est l'impact de AuthService.login ?"
    )

    assert result.intent == "impact"
    names = {item.qualified_name for item in result.evidence}
    assert "AuthService.login" in names
    assert "AuthController.login" in names
    assert "Api.login" in names
    assert any(item.source == "graph_impact" for item in result.evidence)
    assert any(step.tool == "impact" for step in result.trace)


def test_triage_agent_classifies_bug_and_returns_sources():
    result = TriageAgent("demo", FakeGraphTools(), FakeRetriever(), FakeLlm()).run(
        "L'application plante quand le token expire."
    )

    assert result.intent == "triage"
    assert any(
        step.tool == "triage_heuristic" and step.args["label"] == "BUG"
        for step in result.trace
    )
    assert result.evidence
    assert result.answer


def test_review_agent_prioritizes_findings_without_database():
    findings = [
        {
            "id": 1,
            "model_name": "vulnerability_detector",
            "label": "dynamic-eval",
            "score": 0.9,
            "file": "src/runner.py",
            "symbol": "run",
            "payload": {"line": 12, "severity": "high", "message": "eval"},
        },
        {
            "id": 2,
            "model_name": "code_smell_detector",
            "label": "long_method",
            "score": 0.4,
            "file": "src/runner.py",
            "symbol": "run",
            "payload": {"line": 12, "detail": "trop long"},
        },
    ]
    result = ReviewAgent(
        "demo",
        FakeRetriever(),
        FakeLlm(),
        findings_provider=lambda repo, limit: findings,
    ).run("Quels sont les risques ?")

    assert result.intent == "review"
    assert result.evidence[0].qualified_name == "run"
    assert result.evidence[0].source == "finding"
    assert "dynamic-eval" in result.evidence[0].reason
    assert any(step.tool == "findings" for step in result.trace)
    assert result.answer


def test_test_plan_agent_returns_scenarios_without_execution_claim():
    llm = FakeLlm()
    result = ScenarioPlannerAgent("demo", FakeGraphTools(), FakeRetriever(), llm).run(
        "Propose des tests pour AuthService.login."
    )

    assert result.intent == "test_plan"
    assert result.agent == "test_plan"
    assert result.evidence
    assert "exécuter" in llm.calls[0][0].lower()
    assert result.answer

