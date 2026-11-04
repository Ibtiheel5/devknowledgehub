import io
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from app.code_intelligence.symbol_extractor import analyze_directory
from app.schemas.code import RepositoryAnalysis

DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "repos"
MAX_ZIP_BYTES = 200 * 1024 * 1024
MAX_ZIP_FILES = 5000

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class InvalidRepositoryUrl(ValueError):
    pass


class InvalidRepositoryName(ValueError):
    pass


class InvalidArchive(ValueError):
    pass


def _remove_tree(path: Path) -> None:
    """Supprime un dépôt existant, y compris les fichiers Git en lecture seule."""
    if not path.exists():
        return

    def make_writable(func, target, _error):
        target_path = Path(target)
        target_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        func(target)

    shutil.rmtree(path, onerror=make_writable)


def validate_git_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise InvalidRepositoryUrl("Seules les URL https:// sont acceptées.")
    return url


def validate_repo_name(name: str) -> str:
    if not _NAME_RE.fullmatch(name) or ".." in name:
        raise InvalidRepositoryName(
            "Nom de dépôt invalide : lettres, chiffres, '.', '_' et '-' uniquement."
        )
    return name


def repo_dir_for(name: str) -> Path:
    return DATA_ROOT / validate_repo_name(name)


def resolve_repo_root(name: str) -> Path:
    """Dossier source persisté pour un projet (déballe un unique dossier racine)."""
    return unwrap_single_dir(repo_dir_for(name))


def unwrap_single_dir(path: Path) -> Path:
    if not path.exists():
        return path
    entries = [p for p in path.iterdir() if p.name != ".git"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return path


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
        _remove_tree(tmp)


def analyze_git_url(url: str) -> RepositoryAnalysis:
    with clone_repository(url) as repo_path:
        return analyze_directory(repo_path)


def clone_repository_to(url: str, dest: Path, timeout: int = 180) -> str:
    """Clone persistant utilisé par l'ingestion projet. Renvoie le SHA du HEAD."""
    validate_git_url(url)
    if dest.exists():
        _remove_tree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--", url, str(dest)],
        check=True,
        capture_output=True,
        timeout=timeout,
    )
    return git_head_sha(dest)


def git_head_sha(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def git_commit_info(repo_path: Path) -> dict:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "log", "-1", "--format=%H%x1f%s%x1f%an%x1f%aI"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    sha, message, author, committed_at = (result.stdout.strip().split("\x1f") + ["", "", ""])[:4]
    return {"sha": sha, "message": message, "author": author, "committed_at": committed_at}


def extract_zip_bytes(data: bytes, dest: Path, *, max_bytes: int = MAX_ZIP_BYTES,
                      max_files: int = MAX_ZIP_FILES) -> None:
    """Extrait une archive en bloquant les chemins absolus, `..`, liens et bombes zip."""
    if len(data) > max_bytes:
        raise InvalidArchive(f"Archive trop volumineuse (max {max_bytes // 1024 // 1024} Mo).")
    if dest.exists():
        _remove_tree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            if len(infos) > max_files:
                raise InvalidArchive(f"Archive avec trop de fichiers (max {max_files}).")
            for info in infos:
                raw = info.filename.replace("\\", "/")
                member = PurePosixPath(raw)
                if member.is_absolute() or ".." in member.parts:
                    raise InvalidArchive(f"Chemin interdit dans l'archive : {raw}")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise InvalidArchive(f"Lien symbolique interdit dans l'archive : {raw}")
                if info.is_dir():
                    continue
                total += info.file_size
                if total > max_bytes:
                    raise InvalidArchive(
                        f"Contenu décompressé trop volumineux (max {max_bytes // 1024 // 1024} Mo)."
                    )
                target = dest.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
    except zipfile.BadZipFile as exc:
        raise InvalidArchive("Fichier ZIP invalide.") from exc
