from collections import Counter
from pathlib import Path

from app.code_intelligence.language_detector import iter_source_files
from app.code_intelligence.parsers.python_parser import PythonParser
from app.schemas.code import FileAnalysis, RepositoryAnalysis

# Langages réellement parsés. Java et JS/TS viendront ensuite.
_PARSERS = {"python": PythonParser()}


def analyze_directory(root: Path) -> RepositoryAnalysis:
    root = root.resolve()
    languages: Counter[str] = Counter()
    files: list[FileAnalysis] = []

    for path, lang in iter_source_files(root):
        languages[lang] += 1
        parser = _PARSERS.get(lang)
        if parser is None:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            files.append(parser.parse(source, rel))
        except Exception:
            continue  # un fichier illisible ne doit pas casser toute l'analyse

    return RepositoryAnalysis(root=str(root), languages=dict(languages), files=files)
