from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Une preuve citable : un symbole du code avec son emplacement exact."""

    id: str | None = None
    qualified_name: str
    kind: str | None = None
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    score: float = 0.0
    reason: str  # pourquoi ce résultat a été retenu (match exact, appelant de X, ...)
    source: Literal["rag", "symbol_search", "graph_callers", "graph_callees", "overview"] = (
        "symbol_search"
    )
    snippet: str | None = None

    @property
    def citation(self) -> str:
        if not self.file:
            return self.qualified_name
        if self.start_line and self.end_line:
            return f"{self.file}:{self.start_line}-{self.end_line}"
        return self.file


class ToolCall(BaseModel):
    """Trace d'une étape de l'agent (utile pour le debug, l'évaluation et le rapport PFE)."""

    tool: str
    args: dict
    n_results: int


class SearchRequest(BaseModel):
    repo_name: str
    question: str = Field(min_length=3, max_length=1000)
    max_results: int = Field(default=10, ge=1, le=30)


class AgentAskRequest(BaseModel):
    repo_name: str
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=8, ge=1, le=20)


class AgentCitation(BaseModel):
    id: str
    source: Literal["code", "graph"]
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None


class AgentResponse(BaseModel):
    question: str
    answer: str
    citations: list[AgentCitation]
    trace: list[ToolCall]
    model: str | None = None


class ProjectOverview(BaseModel):
    stats: dict
    top_files: list[dict]
    top_modules: list[dict]
    top_symbols: list[Evidence]


class SearchResponse(BaseModel):
    intent: Literal["search", "overview"] = "search"
    overview: ProjectOverview | None = None
    question: str
    answer: str | None = None
    model: str | None = None
    terms: list[str]
    evidence: list[Evidence]
    trace: list[ToolCall]
