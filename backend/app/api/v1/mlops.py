from fastapi import APIRouter, Query

from app.mlops.monitoring_store import MonitoringStore
from app.mlops.run_store import AgentRunStore
from app.schemas.mlops import MetricCreate

router = APIRouter(prefix="/api/v1/mlops", tags=["mlops"])


@router.get("/agent-runs")
def agent_runs(limit: int = Query(default=50, ge=1, le=200)):
    store = AgentRunStore()
    store.ensure_schema()
    return {"summary": store.summary(), "runs": store.recent(limit)}


@router.get("/monitoring")
def monitoring(
    repo_name: str | None = None,
    days: int = Query(default=7, ge=1, le=90),
):
    store = MonitoringStore()
    store.ensure_schema()
    return store.overview(repo_name=repo_name, days=days)


@router.get("/models")
def models(repo_name: str | None = None):
    store = MonitoringStore()
    store.ensure_schema()
    return {"repo_name": repo_name, "models": store.models(repo_name)}


@router.get("/quality")
def quality(
    repo_name: str | None = None,
    model_name: str | None = None,
):
    store = MonitoringStore()
    store.ensure_schema()
    return store.quality(repo_name=repo_name, model_name=model_name)


@router.get("/evaluation")
def evaluation(
    repo_name: str | None = None,
    model_name: str | None = None,
):
    store = MonitoringStore()
    store.ensure_schema()
    return store.quality(repo_name=repo_name, model_name=model_name)


@router.get("/metrics")
def metrics(
    name: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    store = MonitoringStore()
    store.ensure_schema()
    return {"metrics": store.list_metrics(name, limit)}


@router.post("/metrics", status_code=201)
def record_metric(metric: MetricCreate):
    store = MonitoringStore()
    store.ensure_schema()
    store.record_metric(metric.name, metric.value, metric.labels)
    return {"recorded": True, "name": metric.name}
