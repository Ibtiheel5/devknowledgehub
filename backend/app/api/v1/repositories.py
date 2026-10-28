import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.code import RepositoryAnalysis
from app.services.ingestion_service import InvalidRepositoryUrl, analyze_git_url

router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])


class AnalyzeRequest(BaseModel):
    git_url: str


class AnalyzeSummary(BaseModel):
    languages: dict[str, int]
    files_parsed: int
    symbols: int
    imports: int
    calls: int


class AnalyzeResponse(BaseModel):
    summary: AnalyzeSummary
    analysis: RepositoryAnalysis


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        analysis = analyze_git_url(req.git_url)
    except InvalidRepositoryUrl as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=422, detail="Impossible de cloner ce dépôt.")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Le clonage a pris trop de temps.")

    summary = AnalyzeSummary(
        languages=analysis.languages,
        files_parsed=len(analysis.files),
        symbols=analysis.symbol_count,
        imports=sum(len(f.imports) for f in analysis.files),
        calls=sum(len(f.calls) for f in analysis.files),
    )
    return AnalyzeResponse(summary=summary, analysis=analysis)
