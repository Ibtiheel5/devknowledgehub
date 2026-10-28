"""Search Agent (v1) — trouve dans le knowledge graph les symboles pertinents pour une question.

Volontairement déterministe (pas de LLM) : c'est la base testable sur laquelle viendront se
brancher la recherche vectorielle puis le reranking. Sortie = liste d'`Evidence` citables
(fichier + lignes) que l'Analysis Agent et le Copilot consommeront.
"""
import re

from app.schemas.agents import Evidence, ProjectOverview, SearchResponse, ToolCall

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
    "que", "fait", "fais", "faire", "projet", "cet", "code", "repo", "dépôt", "depot",
    "project", "repository", "quoi", "sert", "mon", "ma", "mes", "ton", "ses", "son", "sa",
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
    def __init__(self, tools, expand_top: int = 3):
        self.tools = tools
        self.expand_top = expand_top

    def run(self, question: str, max_results: int = 10) -> SearchResponse:
        if is_overview_question(question):
            return self._overview(question)
        terms = extract_terms(question)
        trace: list[ToolCall] = []
        found: dict[str, Evidence] = {}

        # 1) recherche de symboles pour chaque terme
        for term in terms:
            hits = self.tools.search_symbols(term)
            trace.append(ToolCall(tool="search_symbols", args={"term": term}, n_results=len(hits)))
            for h in hits:
                score = _score(term, h)
                qn = h["qualified_name"]
                if qn in found and found[qn].score >= score:
                    continue
                found[qn] = Evidence(
                    qualified_name=qn,
                    kind=h.get("kind"),
                    file=h.get("file"),
                    start_line=h.get("start_line"),
                    end_line=h.get("end_line"),
                    score=score,
                    reason=f"correspond à « {term} »",
                    source="symbol_search",
                )

        # 2) expansion par le graphe autour des meilleurs résultats
        top = sorted(found.values(), key=lambda e: -e.score)[: self.expand_top]
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
