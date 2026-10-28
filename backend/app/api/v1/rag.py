import subprocess

from fastapi import APIRouter, HTTPException

from app.db.schema import ensure_schema
from app.rag.embedder import get_embedder
from app.rag.retriever import Retriever
from app.rag.store import ChunkStore
from app.schemas.rag import (
    RagIndexRequest,
    RagIndexResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.ingestion_service import InvalidRepositoryUrl
from app.services.rag_service import index_git_url

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.post("/index", response_model=RagIndexResponse)
def index(req: RagIndexRequest):
    ensure_schema()
    try:
        return index_git_url(req.git_url, req.repo_name, ChunkStore(), get_embedder())
    except InvalidRepositoryUrl as e:
        raise HTTPException(status_code=400, detail=str(e))
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=422, detail="Impossible de cloner ce dépôt.")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Le clonage a pris trop de temps.")


@router.post("/search", response_model=RagSearchResponse)
def search(req: RagSearchRequest):
    return Retriever(ChunkStore(), get_embedder()).search(req.repo_name, req.question, req.top_k)


@router.get("/{repo_name}/stats")
def stats(repo_name: str):
    data = ChunkStore().stats(repo_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Dépôt non indexé.")
    return data
