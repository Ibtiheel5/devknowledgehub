from collections import Counter
from pathlib import Path

from app.code_intelligence.language_detector import iter_source_files
from app.code_intelligence.parsers.python_parser import PythonParser
from app.schemas.code import FileAnalysis, RepositoryAnalysis

try:  # les grammaires sont optionnelles à l'installation
    from app.code_intelligence.parsers.java_parser import JavaParser
except ImportError:  # pragma: no cover - dépend de l'environnement
    JavaParser = None  # type: ignore[assignment,misc]

try:
    from app.code_intelligence.parsers.javascript_parser import JavaScriptParser
except ImportError:  # pragma: no cover - dépend de l'environnement
    JavaScriptParser = None  # type: ignore[assignment,misc]

try:
    from app.code_intelligence.parsers.typescript_parser import (
        TsxParser,
        TypeScriptParser,
    )
except ImportError:  # pragma: no cover - dépend de l'environnement
    TypeScriptParser = None  # type: ignore[assignment,misc]
    TsxParser = None  # type: ignore[assignment,misc]

_PARSERS = {"python": PythonParser()}
if JavaParser is not None:
    _PARSERS["java"] = JavaParser()
if JavaScriptParser is not None:
    _PARSERS["javascript"] = JavaScriptParser()
if TypeScriptParser is not None:
    _PARSERS["typescript"] = TypeScriptParser()
if TsxParser is not None:
    _PARSERS["tsx"] = TsxParser()


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
        except OSError:
            continue  # un fichier illisible ne doit pas casser toute l'analyse

    return RepositoryAnalysis(root=str(root), languages=dict(languages), files=files)
