import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from app.code_intelligence.symbol_extractor import analyze_directory
from app.schemas.code import RepositoryAnalysis


class InvalidRepositoryUrl(ValueError):
    pass


def validate_git_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InvalidRepositoryUrl("Seules les URL https:// sont acceptées.")
    return url


@contextmanager
def clone_repository(url: str, timeout: int = 120):
    """Clone superficiel (--depth 1) dans un dossier temporaire, nettoyé à la sortie."""
    validate_git_url(url)
    tmp = Path(tempfile.mkdtemp(prefix="dkh_repo_"))
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, str(tmp / "repo")],
            check=True,
            capture_output=True,
            timeout=timeout,
        )
        yield tmp / "repo"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def analyze_git_url(url: str) -> RepositoryAnalysis:
    with clone_repository(url) as repo_path:
        return analyze_directory(repo_path)
