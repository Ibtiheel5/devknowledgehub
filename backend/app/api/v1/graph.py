import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.neo4j_client import get_driver
from app.graph.builder import GraphBuilder
from app.graph.queries import (
    get_callees,
    get_callers,
    get_repo_calls,
    get_repo_stats,
    get_repo_symbols,
)
from app.services.ingestion_service import InvalidRepositoryUrl, analyze_git_url

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


class BuildRequest(BaseModel):
    repo_name: str
    git_url: str


@router.post("/build")
def build_graph(req: BuildRequest):
    try:
        analysis = analyze_git_url(req.git_url)
    except InvalidRepositoryUrl as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=422, detail="Impossible de cloner ce dépôt.")
    except subprocess.TimeoutExpired as e:
        raise HTTPException(
            status_code=504,
            detail="Le clonage a pris plus de 120 secondes. Vérifiez l'URL et la connexion, puis réessayez.",
        ) from e

    counts = GraphBuilder(get_driver()).build(analysis, req.repo_name)
    return {"repo_name": req.repo_name, **counts}


@router.get("/{repo_name}/callers")
def callers(repo_name: str, qualified_name: str):
    return get_callers(get_driver(), repo_name, qualified_name)


@router.get("/{repo_name}/callees")
def callees(repo_name: str, qualified_name: str):
    return get_callees(get_driver(), repo_name, qualified_name)


@router.get("/{repo_name}/stats")
def stats(repo_name: str):
    return get_repo_stats(get_driver(), repo_name)


@router.get("/{repo_name}/calls")
def calls(repo_name: str, limit: int = 50):
    return get_repo_calls(get_driver(), repo_name, max(1, min(limit, 200)))


@router.get("/{repo_name}/symbols")
def symbols(repo_name: str, limit: int = 50):
    return get_repo_symbols(get_driver(), repo_name, max(1, min(limit, 200)))
