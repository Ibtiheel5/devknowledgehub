from pathlib import Path

from app.code_intelligence.symbol_extractor import analyze_directory


def test_analyze_directory_ignores_technical_dirs(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("def f():\n    pass\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.py").write_text("def g():\n    pass\n")
    (tmp_path / "Main.java").write_text("class Main {}")

    r = analyze_directory(tmp_path)

    assert r.languages == {"python": 1, "java": 1}
    assert [f.path for f in r.files] == ["pkg/a.py"]
    assert r.symbol_count == 1
