import io
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from neo4j.exceptions import Neo4jError

from app.agents.ollama_client import OllamaError
from app.code_intelligence.symbol_extractor import analyze_directory
from app.db.neo4j_client import get_driver
from app.graph.extras import add_issues, issue_graph_row
from app.graph.queries import get_repo_overview, get_repo_stats
from app.graph.schema import symbol_id
from app.rag.store import ChunkStore
from app.schemas.projects import (
    AskRequest,
    FeedbackRequest,
    IngestRequest,
    IssueCreate,
    ProjectCreate,
)
from app.services.assistant_service import ask as ask_assistant
from app.services.content_service import classify_issue
from app.services.ingestion_service import (
    MAX_ZIP_BYTES,
    InvalidRepositoryName,
    InvalidRepositoryUrl,
    resolve_repo_root,
    validate_git_url,
    validate_repo_name,
)
from app.services.project_ingestion import run_ingestion
from app.services.project_store import ProjectStore

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _store() -> ProjectStore:
    store = ProjectStore()
    store.ensure_schema()
    return store


def _get_or_404(store: ProjectStore, name: str) -> dict:
    project = store.get(name)
    if project is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    return project


def _link_issues(name: str, issues: list[dict]) -> str | None:
    """Relie les tickets aux fichiers/symboles du graphe (best-effort)."""
    try:
        root = resolve_repo_root(name)
        if not root.exists():
            return "Sources du projet non disponibles : tickets non reliés au graphe."
        analysis = analyze_directory(root)
        file_paths = [f.path for f in analysis.files]
        symbol_ids = {
            s.qualified_name: symbol_id(name, f.path, s.qualified_name)
            for f in analysis.files
            for s in f.symbols
        }
        rows = [issue_graph_row(name, issue, file_paths, symbol_ids) for issue in issues]
        add_issues(get_driver(), name, rows)
        return None
    except Exception as exc:  # noqa: BLE001 - le graphe ne doit pas bloquer l'API
        return f"Graphe indisponible : {exc}"


@router.post("")
def create_project(req: ProjectCreate):
    try:
        validate_repo_name(req.name)
        if req.source_type == "git" and req.git_url:
            validate_git_url(req.git_url)
    except (InvalidRepositoryName, InvalidRepositoryUrl) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _store().create(req.name, req.git_url, req.source_type)


@router.get("")
def list_projects(limit: int = Query(default=100, ge=1, le=500)):
    return _store().list_projects(limit)


@router.get("/{name}")
def get_project(name: str):
    store = _store()
    project = _get_or_404(store, name)
    return {
        **project,
        "rag": ChunkStore().stats(name),
        "latest_run": store.latest_run(name),
    }


@router.post("/{name}/ingest", status_code=202)
def ingest_git(name: str, background: BackgroundTasks, req: IngestRequest | None = None):
    store = _store()
    project = _get_or_404(store, name)
    target = (req.git_url if req else None) or project.get("git_url")
    if not target:
        raise HTTPException(status_code=400, detail="Aucune URL Git fournie pour ce projet.")
    try:
        validate_git_url(target)
    except InvalidRepositoryUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = store.create_run(project["id"], "git")
    store.set_status(name, "pending", error=None)
    background.add_task(run_ingestion, name, run_id, git_url=target)
    return {"project": store.get(name), "run_id": run_id, "status": "pending"}


@router.post("/{name}/ingest/zip", status_code=202)
async def ingest_zip(
    name: str,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
):
    store = _store()
    project = _get_or_404(store, name)
    data = await file.read(MAX_ZIP_BYTES + 1)
    if len(data) > MAX_ZIP_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Archive trop volumineuse (max {MAX_ZIP_BYTES // 1024 // 1024} Mo).",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Archive vide.")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise HTTPException(status_code=400, detail="Fichier ZIP invalide.")
    run_id = store.create_run(project["id"], "zip")
    store.set_status(name, "pending", error=None)
    background.add_task(run_ingestion, name, run_id, zip_bytes=data)
    return {"project": store.get(name), "run_id": run_id, "status": "pending"}


@router.get("/{name}/status")
def ingestion_status(name: str, limit: int = Query(default=10, ge=1, le=100)):
    store = _store()
    project = _get_or_404(store, name)
    return {
        "repo_name": name,
        "status": project["status"],
        "error": project["error"],
        "commit_sha": project["commit_sha"],
        "languages": project["languages"],
        "technologies": project["technologies"],
        "project_type": project["project_type"],
        "latest_run": store.latest_run(name),
        "runs": store.list_runs(name, limit),
    }


@router.get("/{name}/documents")
def documents(
    name: str,
    include_content: bool = False,
    limit: int = Query(default=200, ge=1, le=500),
):
    store = _store()
    _get_or_404(store, name)
    return {
        "repo_name": name,
        "documents": store.list_documents(name, limit, include_content),
    }


@router.get("/{name}/documents/{path:path}")
def document(name: str, path: str):
    store = _store()
    _get_or_404(store, name)
    doc = store.get_document(name, path)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return doc


@router.get("/{name}/issues")
def issues(name: str, limit: int = Query(default=200, ge=1, le=500)):
    store = _store()
    _get_or_404(store, name)
    return {"repo_name": name, "issues": store.list_issues(name, limit)}


@router.post("/{name}/issues", status_code=201)
def create_issue(name: str, req: IssueCreate):
    store = _store()
    _get_or_404(store, name)
    kind = req.kind or classify_issue(req.title, req.description)
    issue = store.add_issue(
        name,
        req.title,
        description=req.description,
        kind=kind,
        status=req.status,
        external_id=req.external_id,
        labels=req.labels,
    )
    graph_warning = _link_issues(name, [issue])
    return {"issue": issue, "graph_warning": graph_warning}


@router.post("/{name}/issues/import", status_code=201)
def import_issues(name: str, req: list[IssueCreate]):
    store = _store()
    _get_or_404(store, name)
    created = [
        store.add_issue(
            name,
            item.title,
            description=item.description,
            kind=item.kind or classify_issue(item.title, item.description),
            status=item.status,
            external_id=item.external_id,
            labels=item.labels,
        )
        for item in req
    ]
    graph_warning = _link_issues(name, created)
    return {"imported": len(created), "issues": created, "graph_warning": graph_warning}


@router.get("/{name}/findings")
def findings(
    name: str,
    model_name: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    store = _store()
    _get_or_404(store, name)
    return {
        "repo_name": name,
        "findings": store.list_findings(name, limit, model_name),
    }


@router.get("/{name}/architecture")
def architecture(name: str):
    store = _store()
    project = _get_or_404(store, name)
    try:
        overview = get_repo_overview(get_driver(), name)
    except (Neo4jError, OSError):
        overview = {"files": [], "modules": []}
    return {
        "repo_name": name,
        "languages": project["languages"],
        "technologies": project["technologies"],
        "project_type": project["project_type"],
        "commit_sha": project["commit_sha"],
        "overview": overview,
    }


@router.get("/{name}/graph")
def graph(name: str):
    _get_or_404(_store(), name)
    try:
        driver = get_driver()
        return {
            "repo_name": name,
            "stats": get_repo_stats(driver, name),
            "overview": get_repo_overview(driver, name),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Graphe indisponible : {exc}") from exc


@router.post("/{name}/ask")
def ask(name: str, req: AskRequest):
    _get_or_404(_store(), name)
    try:
        return ask_assistant(name, req.question, req.top_k)
    except OllamaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{name}/feedback")
def feedback(name: str, req: FeedbackRequest):
    _get_or_404(_store(), name)
    try:
        _store().add_feedback(req.query_id, req.rating, req.comment)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/{name}/files/{path:path}")
def file_snippet(
    name: str,
    path: str,
    start_line: int | None = Query(default=None, ge=1),
    end_line: int | None = Query(default=None, ge=1),
):
    root = resolve_repo_root(name)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Sources du projet non disponibles.")
    candidate = (Path(root) / path).resolve()
    try:
        candidate.relative_to(Path(root).resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Chemin interdit.") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    try:
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise HTTPException(status_code=422, detail="Fichier illisible.") from exc

    start = start_line or 1
    end = min(end_line or len(lines), len(lines))
    if start > end:
        raise HTTPException(status_code=400, detail="Plage de lignes invalide.")
    return {
        "repo_name": name,
        "path": path,
        "start_line": start,
        "end_line": end,
        "total_lines": len(lines),
        "content": "\n".join(lines[start - 1 : end]),
    }
