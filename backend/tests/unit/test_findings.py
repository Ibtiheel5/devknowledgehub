from pathlib import Path

from app.code_intelligence.findings import analyze_repository_findings
from app.code_intelligence.symbol_extractor import analyze_directory


def _long_function() -> str:
    body = "\n".join(f"    value_{index} = {index}" for index in range(42))
    return f"def risky_function(a, b, c, d, e, f):\n{body}\n    import os\n    os.system('ls')\n"


def test_findings_cover_vulnerabilities_smells_and_clones(tmp_path: Path):
    duplicated = "def total(items):\n    return sum(item.price for item in items)\n"
    (tmp_path / "bad.py").write_text(
        "import pickle\npassword = 'supersecret123'\n" + _long_function()
    )
    (tmp_path / "clone_a.py").write_text(duplicated + "CONSTANT_A = 1\n")
    (tmp_path / "clone_b.py").write_text(duplicated + "CONSTANT_B = 2\n")
    (tmp_path / "clean.py").write_text("def add(a, b):\n    return a + b\n")

    analysis = analyze_directory(tmp_path)
    findings = analyze_repository_findings(analysis, tmp_path)
    models = {finding["model_name"] for finding in findings}
    labels = {finding["label"] for finding in findings}

    assert {"vulnerability_detector", "code_smell_detector", "clone_detector"} <= models
    assert {"hardcoded-secret", "os-system", "long_method", "long_parameter_list"} <= labels
    assert any(finding["target_type"] == "file_pair" for finding in findings)
    assert all(finding["target_id"] for finding in findings)


def test_clean_repository_has_no_high_severity_finding(tmp_path: Path):
    (tmp_path / "clean.py").write_text("def add(a, b):\n    return a + b\n")
    analysis = analyze_directory(tmp_path)
    findings = analyze_repository_findings(analysis, tmp_path)
    high = [
        finding
        for finding in findings
        if finding["model_name"] == "vulnerability_detector"
        and finding["payload"].get("severity") == "high"
    ]
    assert high == []
