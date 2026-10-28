"""Deterministic hybrid search over repository chunks and Knowledge Graph symbols."""
import re
from typing import Protocol

from app.schemas.agents import Evidence, ProjectOverview, SearchResponse, ToolCall
from app.schemas.rag import RagSearchResponse


class RagSearcher(Protocol):
    def search(self, repo_name: str, question: str, top_k: int) -> RagSearchResponse: ...

STOPWORDS = {
    # français
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "ou", "où", "que", "qui", "quoi",
    "pourquoi", "comment", "quand", "est", "sont", "dans", "sur", "pour", "avec", "après",
    "avant", "pas", "ne", "ce", "cette", "ces", "fonction", "méthode", "classe", "fichier",
    # anglais
    "the", "a", "an", "of", "and", "or", "why", "how", "what", "when", "where", "does", "do",
    "is", "are", "in", "on", "for", "with", "after", "before", "not", "this", "that", "fail",
    "fails", "failing", "function", "method", "class", "file", "to", "it", "my", "i",
    # questions générales / mots courants
    "fait", "fais", "faire", "projet", "cet", "code", "repo", "dépôt", "depot",
    "project", "repository", "sert", "mon", "ma", "mes", "ton", "ses", "son", "sa",
    "peut", "peux", "veux", "donne", "moi", "montre", "trouve", "svp", "stp", "merci",
    "par", "plus", "moins", "très", "bien", "mais", "donc", "aux", "est-ce", "être", "avoir",
}

OVERVIEW_RE = re.compile(
    r"(que fait|qu['’]est[- ]ce que|à quoi sert|a quoi sert|c['’]est quoi|r[ée]sum|pr[ée]sente|"
    r"aper[cç]u|vue d['’]ensemble|overview|summar|what does (this|the|my) (project|repo)|"
    r"structure|architecture|explique (ce|le|mon) (projet|d[ée]p[oô]t))",
    re.IGNORECASE,
)


def is_overview_question(question: str) -> bool:
    return bool(OVERVIEW_RE.search(question))

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def extract_terms(question: str, max_terms: int = 6) -> list[str]:
    """Extrait les identifiants probables : snake_case, CamelCase, a.b.c passent en premier."""
    seen: dict[str, int] = {}
    for raw in IDENT_RE.findall(question):
        tok = raw.strip(".")
        if len(tok) < 3 or tok.lower() in STOPWORDS:
            continue
        # priorité : ressemble à un identifiant de code
        prio = 0 if ("_" in tok or "." in tok or CAMEL_RE.search(tok)) else 1
        seen.setdefault(tok, prio)
    ordered = sorted(seen, key=lambda t: (seen[t], -len(t)))
    return ordered[:max_terms]


def _score(term: str, hit: dict) -> float:
    t = term.lower()
    name = (hit.get("name") or "").lower()
    qn = (hit.get("qualified_name") or "").lower()
    if t in (name, qn):
        return 3.0
    if name.startswith(t):
        return 2.0
    if t in name:
        return 1.5
    return 1.0 if t in qn else 0.0


class SearchAgent:
    def __init__(
        self,
        tools,
        expand_top: int = 3,
        retriever: RagSearcher | None = None,
        repo_name: str | None = None,
    ):
        self.tools = tools
        self.expand_top = expand_top
        self.retriever = retriever
        self.repo_name = repo_name

    def run(self, question: str, max_results: int = 10) -> SearchResponse:
        trace: list[ToolCall] = []
        found: dict[str, Evidence] = {}

        if self.retriever and self.repo_name:
            rag_result = self.retriever.search(self.repo_name, question, max_results)
            trace.append(
                ToolCall(tool="rag_search", args={"top_k": max_results}, n_results=len(rag_result.hits))
            )
            for hit in rag_result.hits:
                qualified_name = hit.symbol or hit.file
                evidence = Evidence(
                    qualified_name=qualified_name,
                    kind=hit.kind,
                    file=hit.file,
                    start_line=hit.start_line,
                    end_line=hit.end_line,
                    score=hit.score,
                    reason="extrait pertinent trouvé par recherche RAG",
                    source="rag",
                    snippet=hit.snippet,
                )
                existing = found.get(qualified_name)
                if existing:
                    existing.snippet = hit.snippet
                    existing.score = max(existing.score, hit.score)
                    existing.source = "rag"
                    existing.reason += " et confirmé par le graphe"
                else:
                    found[qualified_name] = evidence

        if is_overview_question(question):
            overview = self._overview(question)
            for evidence in overview.evidence:
                found.setdefault(evidence.qualified_name, evidence)
            overview.evidence = sorted(
                found.values(), key=lambda evidence: (-evidence.score, evidence.qualified_name)
            )[:max_results]
            overview.trace.extend(trace)
            return overview

        terms = extract_terms(question)

        # 1) recherche de symboles pour chaque terme
        for term in terms:
            hits = self.tools.search_symbols(term)
            trace.append(ToolCall(tool="search_symbols", args={"term": term}, n_results=len(hits)))
            for h in hits:
                score = _score(term, h)
                qn = h["qualified_name"]
                existing = found.get(qn)
                if existing and existing.score >= score:
                    continue
                evidence = Evidence(
                    qualified_name=qn,
                    kind=h.get("kind"),
                    file=h.get("file"),
                    start_line=h.get("start_line"),
                    end_line=h.get("end_line"),
                    score=score,
                    reason=f"correspond à « {term} »",
                    source="symbol_search",
                )
                if existing and existing.snippet:
                    evidence.snippet = existing.snippet
                    evidence.source = "rag"
                    evidence.reason += " et confirmé par le graphe"
                found[qn] = evidence

        # 2) expansion par le graphe autour des meilleurs résultats
        top = sorted(
            (evidence for evidence in found.values() if evidence.qualified_name != evidence.file),
            key=lambda evidence: -evidence.score,
        )[: self.expand_top]
        for ev in top:
            for tool_name, source, label in (
                ("callers", "graph_callers", "appelle"),
                ("callees", "graph_callees", "est appelé par"),
            ):
                rows = getattr(self.tools, tool_name)(ev.qualified_name)
                trace.append(
                    ToolCall(tool=tool_name, args={"qualified_name": ev.qualified_name},
                             n_results=len(rows))
                )
                for row in rows:
                    qn = row["qualified_name"]
                    if qn in found:
                        continue
                    found[qn] = Evidence(
                        qualified_name=qn,
                        kind=row.get("kind"),
                        score=ev.score * 0.5,
                        reason=f"{'appelant' if tool_name == 'callers' else 'appelé'} de "
                               f"{ev.qualified_name} (ligne {row.get('line')})",
                        source=source,
                    )

        ranked = sorted(found.values(), key=lambda e: (-e.score, e.qualified_name))
        return SearchResponse(
            question=question, terms=terms, evidence=ranked[:max_results], trace=trace
        )

    def _overview(self, question: str) -> SearchResponse:
        data = self.tools.overview()
        top_symbols = [
            Evidence(
                qualified_name=sym["qualified_name"],
                kind=sym.get("kind"),
                file=sym.get("file"),
                start_line=sym.get("start_line"),
                end_line=sym.get("end_line"),
                score=float(sym.get("degree") or 0),
                reason=f"symbole central ({sym.get('degree', 0)} relations)",
                source="overview",
            )
            for sym in data.get("symbols", [])
        ]
        overview = ProjectOverview(
            stats=data.get("stats", {}),
            top_files=data.get("files", []),
            top_modules=data.get("modules", []),
            top_symbols=top_symbols,
        )
        return SearchResponse(
            intent="overview",
            question=question,
            terms=[],
            evidence=top_symbols,
            overview=overview,
            trace=[ToolCall(tool="overview", args={}, n_results=len(top_symbols))],
        )
