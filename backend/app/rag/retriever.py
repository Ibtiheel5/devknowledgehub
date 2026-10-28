"""Retriever : recherche vectorielle + léger reranking lexical sur les noms de symboles."""
from app.agents.search_agent import extract_terms
from app.rag.embedder import Embedder
from app.schemas.rag import RagHit, RagSearchResponse


class Retriever:
    def __init__(self, store, embedder: Embedder, overfetch: int = 3):
        self.store, self.embedder, self.overfetch = store, embedder, overfetch

    def search(self, repo_name: str, question: str, top_k: int = 8) -> RagSearchResponse:
        qvec = self.embedder.embed([question])[0]
        rows = self.store.search(repo_name, qvec, top_k * self.overfetch)
        terms = [t.lower() for t in extract_terms(question)]

        hits = []
        for r in rows:
            sym = (r["symbol"] or "").lower()
            name = sym.rsplit(".", 1)[-1]
            boost = 0.0
            for t in terms:
                if t == name:
                    boost += 0.20
                elif t in sym:
                    boost += 0.10
                elif t in r["content"].lower():
                    boost += 0.03
            hits.append(RagHit(
                file=r["file"], kind=r["kind"], symbol=r["symbol"],
                start_line=r["start_line"], end_line=r["end_line"],
                score=round(r["score"] + boost, 4), vector_score=round(r["score"], 4),
                snippet=r["content"][:1200],
            ))
        hits.sort(key=lambda h: -h.score)
        return RagSearchResponse(question=question, terms=terms, hits=hits[:top_k])
