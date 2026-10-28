"""Découpe le code en chunks alignés sur les symboles (fonction, méthode, classe).

Le champ `symbol` reprend le `qualified_name` du knowledge graph : un résultat de recherche
vectorielle peut donc être étendu par le graphe (appelants / appelés) sans jointure floue.
"""
from dataclasses import dataclass
from pathlib import Path

from app.schemas.code import FileAnalysis, RepositoryAnalysis


@dataclass(frozen=True)
class Chunk:
    file: str
    kind: str
    symbol: str | None
    language: str
    start_line: int
    end_line: int
    content: str

    @property
    def embedding_text(self) -> str:
        """Texte réellement embeddé : un en-tête de contexte aide à retrouver par nom/chemin."""
        head = f"{self.file} {self.kind} {self.symbol or ''}".strip()
        return f"{head}\n{self.content}"


def _windows(start: int, end: int, size: int, overlap: int) -> list[tuple[int, int]]:
    """Fenêtres [start, end] (1-indexées, inclusives) de `size` lignes avec recouvrement."""
    if end - start + 1 <= size:
        return [(start, end)]
    out, cur = [], start
    while cur <= end:
        stop = min(cur + size - 1, end)
        out.append((cur, stop))
        if stop == end:
            break
        cur = stop - overlap + 1
    return out


def _emit(lines: list[str], fa: FileAnalysis, kind: str, symbol: str | None,
          start: int, end: int, size: int, overlap: int) -> list[Chunk]:
    chunks = []
    for s, e in _windows(start, min(end, len(lines)), size, overlap):
        text = "\n".join(lines[s - 1:e]).strip("\n")
        if text.strip():
            chunks.append(Chunk(fa.path, kind, symbol, fa.language, s, e, text))
    return chunks


def chunk_file(fa: FileAnalysis, source: str, max_lines: int = 80, overlap: int = 10) -> list[Chunk]:
    lines = source.splitlines()
    if not lines:
        return []
    if not fa.symbols:
        return _emit(lines, fa, "window", None, 1, len(lines), max_lines, overlap)

    symbols = sorted(fa.symbols, key=lambda s: (s.start_line, -s.end_line))
    chunks: list[Chunk] = []

    # En-tête du module : imports, constantes, docstring (avant le premier symbole).
    first = symbols[0].start_line
    if first > 1:
        chunks += _emit(lines, fa, "module", None, 1, first - 1, max_lines, overlap)

    for sym in symbols:
        end = sym.end_line
        if sym.kind == "class":
            # Une classe = son en-tête (docstring, attributs) ; ses méthodes ont leurs chunks.
            children = [c.start_line for c in symbols if c.parent == sym.qualified_name]
            if children:
                end = min(children) - 1
            if end < sym.start_line:
                continue
        chunks += _emit(lines, fa, sym.kind, sym.qualified_name,
                        sym.start_line, end, max_lines, overlap)
    return chunks


def build_chunks(root: Path, analysis: RepositoryAnalysis, **kw) -> list[Chunk]:
    chunks: list[Chunk] = []
    for fa in analysis.files:
        try:
            source = (root / fa.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks += chunk_file(fa, source, **kw)
    return chunks
