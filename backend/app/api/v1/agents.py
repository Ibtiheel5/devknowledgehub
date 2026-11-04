from time import perf_counter

from fastapi import APIRouter, HTTPException

from app.agents.ollama_client import OllamaChatClient, OllamaError
from app.agents.research_agent import ResearchAgent
from app.agents.specialist_agents import AGENT_CATALOG, AGENT_NAMES, run_agent
from app.config import settings
from app.db.neo4j_client import get_driver
from app.mlops.run_store import AgentRunStore
from app.rag.embedder import get_embedder
from app.rag.retriever import Retriever
from app.rag.store import ChunkStore
from app.schemas.agents import (
    AgentAskRequest,
    AgentCatalogResponse,
    AgentResponse,
    SearchRequest,
    SearchResponse,
    SpecialistAgentRequest,
)
from app.services.assistant_service import ask as ask_assistant
from app.tools.graph_tools import GraphTools

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/catalog", response_model=AgentCatalogResponse)
def catalog():
    return {"agents": AGENT_CATALOG}


@router.post("/ask", response_model=AgentResponse)
def ask(req: AgentAskRequest):
    started = perf_counter()
    try:
        return ask_assistant(req.repo_name, req.question, req.top_k)
    except OllamaError as exc:
        run_store = AgentRunStore()
        run_store.ensure_schema()
        run_store.record(
            repo_name=req.repo_name,
            agent="copilot",
            model=settings.ollama_model,
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    started = perf_counter()
    llm = OllamaChatClient(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout
    )
    run_store = AgentRunStore()
    run_store.ensure_schema()
    agent = ResearchAgent(
        req.repo_name,
        GraphTools(get_driver(), req.repo_name),
        Retriever(ChunkStore(), get_embedder()),
        llm,
    )
    try:
        response = agent.run(req.question, req.max_results)
    except OllamaError as exc:
        run_store.record(
            repo_name=req.repo_name,
            agent="researcher",
            model=settings.ollama_model,
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    response.agent = "researcher"
    run_store.record(
        repo_name=req.repo_name,
        agent="researcher",
        model=response.model or settings.ollama_model,
        status="success",
        duration_ms=round((perf_counter() - started) * 1000),
        retrieved_chunks=sum(
            call.n_results for call in response.trace if call.tool == "rag_search"
        ),
        graph_evidence=sum(
            item.source in {
                "symbol_search",
                "graph_callers",
                "graph_callees",
                "graph_impact",
            }
            for item in response.evidence
        ),
        citations=sum(item.id is not None for item in response.evidence),
    )
    return response


@router.post("/specialist", response_model=SearchResponse)
def specialist(req: SpecialistAgentRequest):
    if req.agent not in AGENT_NAMES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Agent inconnu : {req.agent}. "
                f"Agents disponibles : {', '.join(sorted(AGENT_NAMES))}."
            ),
        )

    started = perf_counter()
    run_store = AgentRunStore()
    run_store.ensure_schema()
    llm = OllamaChatClient(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout
    )
    graph_tools = GraphTools(get_driver(), req.repo_name)
    retriever = Retriever(ChunkStore(), get_embedder())

    try:
        response = run_agent(
            req.agent,
            req.repo_name,
            req.question,
            graph_tools=graph_tools,
            retriever=retriever,
            llm=llm,
            max_results=req.max_results,
        )
    except OllamaError as exc:
        run_store.record(
            repo_name=req.repo_name,
            agent=req.agent,
            model=settings.ollama_model,
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    run_store.record(
        repo_name=req.repo_name,
        agent=req.agent,
        model=response.model or settings.ollama_model,
        status="success",
        duration_ms=round((perf_counter() - started) * 1000),
        retrieved_chunks=sum(
            call.n_results for call in response.trace if call.tool == "rag_search"
        ),
        graph_evidence=sum(
            item.source in {
                "symbol_search",
                "graph_callers",
                "graph_callees",
                "graph_impact",
            }
            for item in response.evidence
        ),
        citations=sum(item.id is not None for item in response.evidence),
    )
    return response
