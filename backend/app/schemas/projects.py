from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    git_url: str | None = None
    source_type: Literal["git", "zip", "local"] = "git"


class IngestRequest(BaseModel):
    git_url: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=8, ge=1, le=20)


class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    description: str | None = Field(default=None, max_length=20_000)
    kind: Literal["BUG", "FEATURE", "TECHNICAL_DEBT", "UNKNOWN"] | None = None
    status: str = Field(default="open", max_length=50)
    external_id: str | None = Field(default=None, max_length=200)
    labels: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    query_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
