import io
import stat
import zipfile
from pathlib import Path

import pytest

from app.services.ingestion_service import (
    InvalidArchive,
    InvalidRepositoryName,
    InvalidRepositoryUrl,
    _remove_tree,
    extract_zip_bytes,
    unwrap_single_dir,
    validate_git_url,
    validate_repo_name,
)


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def test_extract_zip_writes_files(tmp_path: Path):
    data = _zip({"src/App.java": b"class App {}", "README.md": b"# demo"})
    dest = tmp_path / "repo"
    extract_zip_bytes(data, dest)

    assert (dest / "src" / "App.java").read_bytes() == b"class App {}"
    assert (dest / "README.md").read_text() == "# demo"


def test_extract_zip_rejects_path_traversal(tmp_path: Path):
    data = _zip({"../evil.py": b"print('boom')"})
    with pytest.raises(InvalidArchive):
        extract_zip_bytes(data, tmp_path / "repo")


def test_extract_zip_rejects_absolute_path(tmp_path: Path):
    data = _zip({"/etc/passwd": b"nope"})
    with pytest.raises(InvalidArchive):
        extract_zip_bytes(data, tmp_path / "repo")


def test_extract_zip_rejects_symlink(tmp_path: Path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "target")
    with pytest.raises(InvalidArchive):
        extract_zip_bytes(buffer.getvalue(), tmp_path / "repo")


def test_extract_zip_rejects_invalid_archive(tmp_path: Path):
    with pytest.raises(InvalidArchive):
        extract_zip_bytes(b"not a zip", tmp_path / "repo")


def test_repo_name_validation():
    assert validate_repo_name("devknowledgehub-main") == "devknowledgehub-main"
    assert validate_repo_name("repo_1.2") == "repo_1.2"
    for bad in ("../etc", "a/b", "", ".hidden", "a b"):
        with pytest.raises(InvalidRepositoryName):
            validate_repo_name(bad)


def test_git_url_requires_https():
    assert validate_git_url("https://github.com/pallets/click.git")
    for bad in ("file:///etc", "http://example.com/repo", "git@github.com:a/b.git"):
        with pytest.raises(InvalidRepositoryUrl):
            validate_git_url(bad)


def test_unwrap_single_root_dir(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "project").mkdir(parents=True)
    (root / "project" / "a.py").write_text("x = 1")
    assert unwrap_single_dir(root) == root / "project"

    (root / "README.md").write_text("demo")
    assert unwrap_single_dir(root) == root


def test_remove_tree_clears_read_only_files(tmp_path: Path):
    repository = tmp_path / "repository"
    pack_file = repository / ".git" / "objects" / "pack" / "pack.idx"
    pack_file.parent.mkdir(parents=True)
    pack_file.write_text("pack", encoding="utf-8")
    pack_file.chmod(stat.S_IRUSR)

    _remove_tree(repository)

    assert not repository.exists()
