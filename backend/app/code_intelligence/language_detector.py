from pathlib import Path

EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".idea", ".vscode", ".pytest_cache", ".mypy_cache", "target",
}

MAX_FILE_BYTES = 1_000_000


def detect_language(path: Path) -> str | None:
    return EXTENSIONS.get(path.suffix.lower())


def iter_source_files(root: Path):
    """Parcourt le dépôt en ignorant dossiers techniques et fichiers trop gros."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        lang = detect_language(path)
        if lang:
            yield path, lang
