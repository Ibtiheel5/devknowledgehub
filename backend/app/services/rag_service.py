from pathlib import Path

from app.code_intelligence.symbol_extractor import analyze_directory
from app.rag.chunker import build_chunks, build_document_chunks
from app.rag.embedder import Embedder
from app.schemas.code import RepositoryAnalysis
from app.schemas.rag import RagIndexResponse
from app.services.content_service import collect_documents
from app.services.ingestion_service import clone_repository

BATCH = 64


def index_analysis(root: Path, analysis: RepositoryAnalysis, repo_name: str,
                   git_url: str | None, store, embedder: Embedder,
                   commit_sha: str | None = None,
                   documents: list[dict] | None = None) -> RagIndexResponse:
    root = root.resolve()
    chunks = build_chunks(root, analysis)
    if documents is None:
        documents = collect_documents(root)
    chunks += build_document_chunks(documents)
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), BATCH):
        vectors += embedder.embed([c.embedding_text for c in chunks[i:i + BATCH]])
    store.replace_repo(repo_name, git_url, chunks, vectors, commit_sha=commit_sha)
    return RagIndexResponse(repo_name=repo_name, files=len({c.file for c in chunks}),
                            chunks=len(chunks), embedder=embedder.name)


def index_directory(root: Path, repo_name: str, git_url: str | None,
                    store, embedder: Embedder,
                    commit_sha: str | None = None) -> RagIndexResponse:
    return index_analysis(
        root, analyze_directory(root), repo_name, git_url, store, embedder, commit_sha
    )


def index_git_url(git_url: str, repo_name: str, store, embedder: Embedder) -> RagIndexResponse:
    with clone_repository(git_url) as repo_path:
        return index_directory(repo_path, repo_name, git_url, store, embedder)
