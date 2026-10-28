from time import perf_counter

from fastapi import APIRouter, HTTPException

from app.agents.code_assistant import CodeAssistantAgent
from app.agents.ollama_client import OllamaChatClient, OllamaError
from app.agents.search_agent import SearchAgent
from app.config import settings
from app.db.neo4j_client import get_driver
from app.mlops.run_store import AgentRunStore
from app.rag.embedder import get_embedder
from app.rag.retriever import Retriever
from app.rag.store import ChunkStore
from app.schemas.agents import AgentAskRequest, AgentResponse, SearchRequest, SearchResponse
from app.tools.graph_tools import GraphTools

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.post("/ask", response_model=AgentResponse)
def ask(req: AgentAskRequest):
    started = perf_counter()
    graph_tools = GraphTools(get_driver(), req.repo_name)
    retriever = Retriever(ChunkStore(), get_embedder())
    llm = OllamaChatClient(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout
    )
    run_store = AgentRunStore()
    run_store.ensure_schema()
    try:
        response = CodeAssistantAgent(req.repo_name, graph_tools, retriever, llm).run(
            req.question, req.top_k
        )
    except OllamaError as exc:
        run_store.record(
            repo_name=req.repo_name,
            model=settings.ollama_model,
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    run_store.record(
        repo_name=req.repo_name,
        model=response.model or settings.ollama_model,
        status="success",
        duration_ms=round((perf_counter() - started) * 1000),
        retrieved_chunks=next(
            (call.n_results for call in response.trace if call.tool == "rag_search"), 0
        ),
        graph_evidence=sum(source.source == "graph" for source in response.citations),
        citations=len(response.citations),
    )
    return response


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    agent = SearchAgent(GraphTools(get_driver(), req.repo_name))
    return agent.run(req.question, req.max_results)
