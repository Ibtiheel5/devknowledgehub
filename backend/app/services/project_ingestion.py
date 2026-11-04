"""Orchestration d'une ingestion projet : source -> analyse -> graphe -> index RAG."""
import logging
from time import perf_counter

from app.code_intelligence.findings import analyze_repository_findings
from app.code_intelligence.symbol_extractor import analyze_directory
from app.code_intelligence.technology_detector import detect_technologies
from app.db.neo4j_client import get_driver
from app.graph.builder import GraphBuilder
from app.graph.extras import (
    add_commit,
    add_documents,
    add_findings,
    add_issues,
    add_technologies,
    issue_graph_row,
)
from app.graph.schema import symbol_id
from app.mlops.monitoring_store import MonitoringStore
from app.rag.embedder import get_embedder
from app.rag.store import ChunkStore
from app.services.content_service import collect_documents
from app.services.ingestion_service import (
    clone_repository_to,
    extract_zip_bytes,
    git_commit_info,
    repo_dir_for,
    unwrap_single_dir,
)
from app.services.project_store import ProjectStore
from app.services.rag_service import index_analysis

logger = logging.getLogger(__name__)


def _symbol_index(project_name: str, analysis) -> dict[str, str]:
    return {
        s.qualified_name: symbol_id(project_name, f.path, s.qualified_name)
        for f in analysis.files
        for s in f.symbols
    }


def run_ingestion(
    project_name: str,
    run_id: int,
    *,
    git_url: str | None = None,
    zip_bytes: bytes | None = None,
) -> None:
    """Exécute l'ingestion complète. Utilisé en arrière-plan par l'API projets."""
    store = ProjectStore()
    store.ensure_schema()
    store.start_run(run_id)
    store.set_status(project_name, "indexing", error=None)
    monitoring = MonitoringStore()
    started = perf_counter()

    commit_sha: str | None = None
    try:
        dest = repo_dir_for(project_name)
        if zip_bytes is not None:
            extract_zip_bytes(zip_bytes, dest)
        else:
            if not git_url:
                raise ValueError("git_url ou archive ZIP requis.")
            commit_sha = clone_repository_to(git_url, dest)

        root = unwrap_single_dir(dest)
        analysis = analyze_directory(root)
        technologies = detect_technologies(root, analysis)
        documents = collect_documents(root)
        findings = analyze_repository_findings(analysis, root)
        store.clear_predictions(project_name)
        store.add_predictions(project_name, findings)

        rag = index_analysis(
            root,
            analysis,
            project_name,
            git_url,
            ChunkStore(),
            get_embedder(),
            commit_sha=commit_sha,
            documents=documents,
        )

        for document in documents:
            store.upsert_document(
                project_name,
                document["path"],
                title=document.get("title"),
                kind=document.get("kind") or "markdown",
                content=document["content"],
            )

        commit: dict | None = None
        if commit_sha:
            info = git_commit_info(dest)
            committed_at = info.get("committed_at") or None
            commit = {
                "sha": commit_sha,
                "message": info.get("message"),
                "author": info.get("author"),
                "committed_at": committed_at,
            }
            store.upsert_commit(
                project_name,
                commit_sha,
                message=commit["message"],
                author=commit["author"],
                committed_at=committed_at,
            )

        graph_error: str | None = None
        try:
            driver = get_driver()
            GraphBuilder(driver).build(analysis, project_name)
            file_paths = [f.path for f in analysis.files]
            symbol_ids = _symbol_index(project_name, analysis)
            add_commit(driver, project_name, commit, file_paths)
            add_technologies(driver, project_name, technologies["technologies"])
            add_documents(
                driver,
                project_name,
                documents,
                file_paths=file_paths,
                symbol_ids=symbol_ids,
            )
            issue_rows = [
                issue_graph_row(project_name, issue, file_paths, symbol_ids)
                for issue in store.list_issues(project_name)
            ]
            add_issues(driver, project_name, issue_rows)
            graph_findings = [
                finding
                for finding in findings
                if finding.get("target_type") == "file" or finding.get("symbol")
            ]
            add_findings(driver, project_name, graph_findings)
        except Exception as exc:  # le graphe est optionnel : le RAG reste utilisable
            graph_error = str(exc)
            logger.exception("Construction du graphe impossible pour %s", project_name)

        store.set_status(
            project_name,
            "ready",
            error=graph_error,
            commit_sha=commit_sha,
            languages=analysis.languages,
            technologies=technologies["technologies"],
            project_type=technologies["project_type"],
        )
        store.finish_run(
            run_id,
            "succeeded",
            files=rag.files,
            chunks=rag.chunks,
            symbols=analysis.symbol_count,
            commit_sha=commit_sha,
        )
        _record_monitoring(
            monitoring,
            project_name,
            "succeeded",
            started,
            findings=len(findings),
        )
    except Exception as exc:
        logger.exception("Ingestion échouée pour %s", project_name)
        message = str(exc)[:1000]
        store.set_status(project_name, "failed", error=message)
        store.finish_run(run_id, "failed", error=message)
        _record_monitoring(monitoring, project_name, "failed", started)


def _record_monitoring(
    monitoring: MonitoringStore,
    project_name: str,
    status: str,
    started: float,
    *,
    findings: int = 0,
) -> None:
    try:
        labels = {"repo_name": project_name, "status": status}
        monitoring.record_metric(
            "ingestion_duration_seconds", round(perf_counter() - started, 3), labels
        )
        monitoring.record_metric("ingestion_findings", findings, labels)
    except Exception:  # la télémétrie ne doit pas casser l'ingestion
        logger.exception("Enregistrement des métriques d'ingestion impossible")
