"""Collecte de la documentation et rapprochement texte -> fichiers/symboles."""
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.code_intelligence.language_detector import IGNORED_DIRS
from app.config import settings

MAX_DOC_BYTES = 1_000_000
MAX_DOCUMENTS = 500
DOC_SUFFIXES = {".md", ".markdown", ".rst"}
logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r"^\s*#\s+(.+)$", re.MULTILINE)

IssueKind = Literal["BUG", "FEATURE", "TECHNICAL_DEBT", "UNKNOWN"]

_KEYWORDS: dict[IssueKind, tuple[str, ...]] = {
    "BUG": (
        "bug", "error", "crash", "exception", "fail", "broken", "regression",
        "nullpointer", "panic", "defect", "erreur", "plante", "ne fonctionne pas",
        "incorrect", "wrong", "500",
    ),
    "FEATURE": (
        "feature", "add support", "support for", "enhancement", "improve",
        "request", "ajouter", "nouvelle fonctionnalité", "would be nice",
        "allow", "enable",
    ),
    "TECHNICAL_DEBT": (
        "refactor", "technical debt", "debt", "cleanup", "clean up", "performance",
        "optimize", "upgrade", "dependency", "coverage", "flaky", "dette",
        "maintainability", "duplicate", "complexity",
    ),
}


def _transformer_model_path() -> Path:
    configured = Path(settings.ticket_classifier_model_path)
    if configured.is_absolute():
        return configured
    return Path(__file__).resolve().parents[3] / configured


def _normalize_model_label(label: str) -> IssueKind:
    normalized = label.strip().upper().replace("-", " ").replace("_", " ")
    if normalized == "BUG":
        return "BUG"
    if normalized == "FEATURE":
        return "FEATURE"
    if normalized in {"TECH DEBT", "TECHNICAL DEBT"}:
        return "TECHNICAL_DEBT"
    return "UNKNOWN"


@lru_cache(maxsize=1)
def _load_transformer_classifier():
    if not settings.ticket_classifier_transformer_enabled:
        return None
    model_path = _transformer_model_path()
    if not model_path.is_dir():
        return None
    try:
        from transformers import pipeline

        return pipeline(
            "text-classification",
            model=str(model_path),
            tokenizer=str(model_path),
            top_k=None,
            truncation=True,
        )
    except (ImportError, OSError, ValueError) as exc:
        logger.warning("Classifieur Transformer indisponible, fallback lexical: %s", exc)
        return None


def _classify_with_transformer(text: str) -> IssueKind | None:
    classifier = _load_transformer_classifier()
    if classifier is None:
        return None
    try:
        predictions = classifier(text)
        candidates = predictions[0] if predictions and isinstance(predictions[0], list) else predictions
        best = max(candidates, key=lambda item: float(item.get("score", 0.0)))
        return _normalize_model_label(str(best.get("label", "")))
    except (KeyError, TypeError, ValueError, IndexError, RuntimeError) as exc:
        logger.warning("Prédiction Transformer impossible, fallback lexical: %s", exc)
        return None


def _read_doc(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_DOC_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect_documents(root: Path, limit: int = MAX_DOCUMENTS) -> list[dict]:
    documents: list[dict] = []
    for path in sorted(root.rglob("*")):
        if len(documents) >= limit:
            break
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        if path.suffix.lower() not in DOC_SUFFIXES:
            continue
        content = _read_doc(path)
        if not content.strip():
            continue
        heading = _HEADING_RE.search(content)
        title = heading.group(1).strip() if heading else path.stem
        documents.append(
            {
                "path": rel.as_posix(),
                "title": title[:200],
                "kind": "markdown" if path.suffix.lower() in {".md", ".markdown"} else "rst",
                "content": content,
            }
        )
    return documents


def classify_issue(
    title: str,
    description: str | None = None,
    *,
    use_transformer: bool = True,
) -> IssueKind:
    text = f"{title} {description or ''}".lower()
    if use_transformer:
        transformer_label = _classify_with_transformer(text)
        if transformer_label is not None and transformer_label != "UNKNOWN":
            return transformer_label
    scores = {
        kind: sum(1 for keyword in keywords if keyword in text)
        for kind, keywords in _KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "UNKNOWN"


def extract_mentions(
    text: str,
    file_paths: list[str],
    symbol_names: list[str],
    limit: int = 20,
) -> tuple[list[str], list[str]]:
    """Rapprochement lexical simple : chemins de fichiers et noms de symboles cités."""
    lowered = text.lower()
    files: list[str] = []
    for path in file_paths:
        basename = path.rsplit("/", 1)[-1].lower()
        if path.lower() in lowered or (len(basename) >= 4 and basename in lowered):
            files.append(path)
        if len(files) >= limit:
            break

    symbols: list[str] = []
    for qualified in symbol_names:
        name = qualified.rsplit(".", 1)[-1]
        if len(name) >= 4 and name.lower() in lowered:
            symbols.append(qualified)
        if len(symbols) >= limit:
            break

    return files, symbols
