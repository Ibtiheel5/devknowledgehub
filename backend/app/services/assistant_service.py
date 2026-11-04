"""Cas d'usage de l'assistant : agent + persistance des métriques d'exécution."""
import logging
from time import perf_counter

from app.agents.code_assistant import CodeAssistantAgent
from app.agents.ollama_client import OllamaChatClient
from app.config import settings
from app.db.neo4j_client import get_driver
from app.mlops.run_store import AgentRunStore
from app.rag.embedder import get_embedder
from app.rag.retriever import Retriever
from app.rag.store import ChunkStore
from app.schemas.agents import AgentResponse
from app.services.project_store import ProjectStore
from app.tools.graph_tools import GraphTools

logger = logging.getLogger(__name__)


def ask(repo_name: str, question: str, top_k: int = 8) -> AgentResponse:
    started = perf_counter()
    graph_tools = GraphTools(get_driver(), repo_name)
    retriever = Retriever(ChunkStore(), get_embedder())
    llm = OllamaChatClient(
        settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout
    )
    run_store = AgentRunStore()
    run_store.ensure_schema()

    response = CodeAssistantAgent(repo_name, graph_tools, retriever, llm).run(question, top_k)
    duration_ms = round((perf_counter() - started) * 1000)

    run_store.record(
        repo_name=repo_name,
        model=response.model or settings.ollama_model,
        status="success",
        duration_ms=duration_ms,
        retrieved_chunks=next(
            (call.n_results for call in response.trace if call.tool == "rag_search"), 0
        ),
        graph_evidence=sum(source.source == "graph" for source in response.citations),
        citations=len(response.citations),
    )
    try:
        response.query_id = ProjectStore().record_rag_query(
            repo_name,
            question,
            answer=response.answer,
            top_k=top_k,
            latency_ms=duration_ms,
            citations=len(response.citations),
        )
    except Exception:  # la persistance analytics ne doit pas casser la réponse
        logger.exception("Enregistrement de la requête RAG impossible")

    return response
