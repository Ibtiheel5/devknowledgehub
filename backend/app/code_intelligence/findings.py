"""Analyses statiques légères exécutées à l'ingestion : vulnérabilités, smells, clones."""
from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

from app.schemas.code import FileAnalysis, RepositoryAnalysis

MAX_FILE_BYTES = 1_000_000
MAX_CLONE_FILES = 200
MAX_CLONE_PAIRS = 5_000

_VULNERABILITY_RULES: list[tuple[str, str, str, str]] = [
    ("dynamic-eval", r"\b(eval|exec)\s*\(", "high", "Exécution de code dynamique"),
    ("shell-true", r"subprocess\.\w+\([^)]*shell\s*=\s*True", "high", "Shell activé dans subprocess"),
    ("os-system", r"\bos\.system\s*\(", "medium", "Commande système via os.system"),
    ("pickle-load", r"\bpickle\.loads?\s*\(", "high", "Désérialisation pickle non sûre"),
    ("yaml-load", r"yaml\.load\s*\((?!.*SafeLoader)", "medium", "yaml.load sans SafeLoader"),
    (
        "hardcoded-secret",
        r"(?i)(password|secret|api[_-]?key|token)\s*=\s*['\"][^'\"]{6,}",
        "high",
        "Secret potentiellement codé en dur",
    ),
    (
        "sql-injection",
        r"(?i)(execute|query)\s*\(\s*f?['\"].*(select|insert|update|delete)",
        "high",
        "Requête SQL construite dynamiquement",
    ),
    ("weak-hash", r"\b(md5|sha1)\s*\(", "low", "Hash cryptographique faible"),
    ("tls-verify-off", r"verify\s*=\s*False", "high", "Vérification TLS désactivée"),
    ("debug-true", r"(?i)debug\s*=\s*True", "low", "Mode debug activé"),
]
_COMPILED_RULES = [
    (name, re.compile(pattern), severity, message)
    for name, pattern, severity, message in _VULNERABILITY_RULES
]
_SEVERITY_WEIGHTS = {"high": 0.4, "medium": 0.2, "low": 0.1}

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]")


def _read_source(root: Path, file: FileAnalysis) -> str | None:
    target = root / file.path
    try:
        if target.stat().st_size > MAX_FILE_BYTES:
            return None
        return target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _risk_score(severities: list[str]) -> float:
    return round(min(1.0, sum(_SEVERITY_WEIGHTS.get(s, 0.0) for s in severities)), 4)


def scan_vulnerabilities(file: FileAnalysis, content: str) -> list[dict]:
    findings: list[dict] = []
    lines = content.splitlines()
    for name, pattern, severity, message in _COMPILED_RULES:
        matches = [
            (line_number, line)
            for line_number, line in enumerate(lines, start=1)
            if pattern.search(line)
        ]
        if not matches:
            continue
        score = _risk_score([severity] * len(matches))
        for line_number, line in matches:
            findings.append(
                {
                    "model_name": "vulnerability_detector",
                    "model_version": "rules-v1",
                    "target_type": "file",
                    "target_id": f"{file.path}:{line_number}:{name}",
                    "file": file.path,
                    "label": name,
                    "score": score,
                    "payload": {
                        "severity": severity,
                        "line": line_number,
                        "message": message,
                        "snippet": line.strip()[:200],
                    },
                }
            )
    return findings


def _parameter_count(signature: str) -> int:
    start = signature.find("(")
    end = signature.find(")", start + 1)
    if start == -1 or end == -1:
        return 0
    params = signature[start + 1 : end].strip()
    if not params:
        return 0
    return len([part for part in params.split(",") if part.strip()])


def scan_code_smells(file: FileAnalysis, content: str) -> list[dict]:
    findings: list[dict] = []
    lines = content.splitlines()
    for symbol in file.symbols:
        if symbol.kind not in {"function", "method"}:
            continue
        length = max(0, symbol.end_line - symbol.start_line + 1)
        signature = lines[symbol.start_line - 1] if symbol.start_line <= len(lines) else ""
        if length > 40:
            findings.append(
                _smell_finding(
                    file,
                    "long_method",
                    symbol,
                    score=round(min(1.0, length / 200), 4),
                    detail=f"{symbol.qualified_name} fait {length} lignes",
                    value=length,
                )
            )
        params = _parameter_count(signature)
        if params > 5:
            findings.append(
                _smell_finding(
                    file,
                    "long_parameter_list",
                    symbol,
                    score=round(min(1.0, params / 12), 4),
                    detail=f"{symbol.qualified_name} a {params} paramètres",
                    value=params,
                )
            )
        if file.language == "python":
            indents = [
                len(line) - len(line.lstrip())
                for line in lines[symbol.start_line - 1 : symbol.end_line]
                if line.strip()
            ]
            if indents:
                depth = max(0, (max(indents) - min(indents)) // 4)
                if depth > 4:
                    findings.append(
                        _smell_finding(
                            file,
                            "deep_nesting",
                            symbol,
                            score=round(min(1.0, depth / 10), 4),
                            detail=f"{symbol.qualified_name} atteint une profondeur {depth}",
                            value=depth,
                        )
                    )
    return findings


def _smell_finding(
    file: FileAnalysis,
    smell: str,
    symbol,
    *,
    score: float,
    detail: str,
    value: int,
) -> dict:
    return {
        "model_name": "code_smell_detector",
        "model_version": "rules-v1",
        "target_type": "symbol",
        "target_id": f"{file.path}:{symbol.start_line}:{smell}",
        "file": file.path,
        "symbol": symbol.qualified_name,
        "label": smell,
        "score": score,
        "payload": {"line": symbol.start_line, "detail": detail, "value": value},
    }


def _token_set(content: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(content)}


def detect_clones(
    sources: list[tuple[FileAnalysis, str]], threshold: float = 0.75
) -> list[dict]:
    candidates = [
        (file, _token_set(content))
        for file, content in sources
        if len(content) > 60 and len(content) < MAX_FILE_BYTES
    ][:MAX_CLONE_FILES]
    findings: list[dict] = []
    pairs = 0
    for (left, left_tokens), (right, right_tokens) in combinations(candidates, 2):
        if left.language != right.language:
            continue
        if not left_tokens or not right_tokens:
            continue
        pairs += 1
        if pairs > MAX_CLONE_PAIRS:
            break
        score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if score < threshold:
            continue
        findings.append(
            {
                "model_name": "clone_detector",
                "model_version": "jaccard-v1",
                "target_type": "file_pair",
                "target_id": f"{left.path}|{right.path}",
                "file": left.path,
                "label": "DUPLICATE",
                "score": round(score, 4),
                "payload": {"other_file": right.path, "similarity": round(score, 4)},
            }
        )
    return findings


def analyze_repository_findings(analysis: RepositoryAnalysis, root: Path) -> list[dict]:
    findings: list[dict] = []
    sources: list[tuple[FileAnalysis, str]] = []
    for file in analysis.files:
        content = _read_source(root, file)
        if content is None:
            continue
        sources.append((file, content))
        findings.extend(scan_vulnerabilities(file, content))
        findings.extend(scan_code_smells(file, content))
    findings.extend(detect_clones(sources))
    return findings
