from fastapi import APIRouter, Query

from app.mlops.run_store import AgentRunStore

router = APIRouter(prefix="/api/v1/mlops", tags=["mlops"])


@router.get("/agent-runs")
def agent_runs(limit: int = Query(default=50, ge=1, le=200)):
    store = AgentRunStore()
    store.ensure_schema()
    return {"summary": store.summary(), "runs": store.recent(limit)}
