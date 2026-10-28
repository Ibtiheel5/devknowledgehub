from pathlib import Path

from app.code_intelligence.symbol_extractor import analyze_directory
from app.rag.chunker import build_chunks
from app.rag.embedder import Embedder
from app.schemas.rag import RagIndexResponse
from app.services.ingestion_service import clone_repository

BATCH = 64


def index_directory(root: Path, repo_name: str, git_url: str | None,
                    store, embedder: Embedder) -> RagIndexResponse:
    analysis = analyze_directory(root)
    chunks = build_chunks(root.resolve(), analysis)
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), BATCH):
        vectors += embedder.embed([c.embedding_text for c in chunks[i:i + BATCH]])
    store.replace_repo(repo_name, git_url, chunks, vectors)
    return RagIndexResponse(repo_name=repo_name, files=len({c.file for c in chunks}),
                            chunks=len(chunks), embedder=embedder.name)


def index_git_url(git_url: str, repo_name: str, store, embedder: Embedder) -> RagIndexResponse:
    with clone_repository(git_url) as repo_path:
        return index_directory(repo_path, repo_name, git_url, store, embedder)
