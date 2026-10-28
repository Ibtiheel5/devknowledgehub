from pydantic import BaseModel, Field


class RagIndexRequest(BaseModel):
    repo_name: str
    git_url: str


class RagIndexResponse(BaseModel):
    repo_name: str
    files: int
    chunks: int
    embedder: str


class RagSearchRequest(BaseModel):
    repo_name: str
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=8, ge=1, le=30)


class RagHit(BaseModel):
    file: str
    kind: str
    symbol: str | None = None
    start_line: int
    end_line: int
    score: float
    vector_score: float
    snippet: str

    @property
    def citation(self) -> str:
        return f"{self.file}:{self.start_line}-{self.end_line}"


class RagSearchResponse(BaseModel):
    question: str
    terms: list[str]
    hits: list[RagHit]
