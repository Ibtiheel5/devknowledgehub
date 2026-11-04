"""Détection baseline de code smells à partir de métriques structurelles."""
import re

_PY_FUNC_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*:")
_BRACE_FUNC_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|abstract|synchronized|async|export)\s+)*"
    r"(?:[\w<>\[\],.?]+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws[\w, .]+)?\{"
)
_CLASS_RE = re.compile(r"^\s*(?:public\s+|private\s+|abstract\s+|export\s+|final\s+)*class\s+(\w+)")
_BRACE_KEYWORDS = {"if", "for", "while", "switch", "catch", "else", "function", "constructor", "do"}


def _param_count(params: str) -> int:
    params = params.strip()
    if not params:
        return 0
    return len([p for p in params.split(",") if p.strip()])


def _python_functions(lines: list[str]) -> list[dict]:
    functions: list[dict] = []
    for index, line in enumerate(lines):
        match = _PY_FUNC_RE.match(line)
        if not match or line.lstrip().startswith(("#", "//")):
            continue
        base_indent = len(line) - len(line.lstrip())
        end = index
        max_indent = base_indent
        for cursor in range(index + 1, len(lines)):
            candidate = lines[cursor]
            stripped = candidate.strip()
            if not stripped:
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= base_indent:
                break
            max_indent = max(max_indent, indent)
            end = cursor
        functions.append(
            {
                "name": match.group(1),
                "start": index + 1,
                "end": end + 1,
                "lines": end - index + 1,
                "params": _param_count(match.group(2)),
                "nesting": max(0, (max_indent - base_indent) // 4),
            }
        )
    return functions


def _brace_functions(source: str) -> list[dict]:
    lines = source.splitlines()
    functions: list[dict] = []
    for index, line in enumerate(lines):
        match = _BRACE_FUNC_RE.match(line)
        if not match or match.group(1) in _BRACE_KEYWORDS:
            continue
        brace = source.find("{", source.find(line))
        if brace == -1:
            continue
        depth = 0
        end_offset = len(source)
        max_depth = 0
        for cursor in range(brace, len(source)):
            char = source[cursor]
            if char == "{":
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end_offset = cursor
                    break
        end_line = source.count("\n", 0, end_offset) + 1
        functions.append(
            {
                "name": match.group(1),
                "start": index + 1,
                "end": end_line,
                "lines": end_line - index + 1,
                "params": _param_count(match.group(2)),
                "nesting": max_depth,
            }
        )
    return functions


def iter_functions(source: str, language: str = "python") -> list[dict]:
    if language == "python":
        return _python_functions(source.splitlines())
    return _brace_functions(source)


def _large_classes(source: str, language: str, threshold: int = 20) -> list[dict]:
    findings: list[dict] = []
    lines = source.splitlines()
    if language != "python":
        return findings
    for index, line in enumerate(lines):
        match = _CLASS_RE.match(line)
        if not match:
            continue
        base_indent = len(line) - len(line.lstrip())
        methods = 0
        for cursor in range(index + 1, len(lines)):
            candidate = lines[cursor]
            if not candidate.strip():
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= base_indent:
                break
            if re.match(r"^\s*(?:async\s+)?def\s+\w+", candidate):
                methods += 1
        if methods > threshold:
            findings.append(
                {
                    "smell": "large_class",
                    "line": index + 1,
                    "value": methods,
                    "detail": f"Classe {match.group(1)} avec {methods} méthodes",
                }
            )
    return findings


def detect_smells(
    source: str,
    language: str = "python",
    *,
    long_method_lines: int = 40,
    max_params: int = 5,
    max_nesting: int = 4,
) -> list[dict]:
    findings: list[dict] = []
    for function in iter_functions(source, language):
        if function["lines"] > long_method_lines:
            findings.append(
                {
                    "smell": "long_method",
                    "line": function["start"],
                    "value": function["lines"],
                    "detail": f"{function['name']} fait {function['lines']} lignes",
                }
            )
        if function["params"] > max_params:
            findings.append(
                {
                    "smell": "long_parameter_list",
                    "line": function["start"],
                    "value": function["params"],
                    "detail": f"{function['name']} a {function['params']} paramètres",
                }
            )
        if function["nesting"] > max_nesting:
            findings.append(
                {
                    "smell": "deep_nesting",
                    "line": function["start"],
                    "value": function["nesting"],
                    "detail": f"{function['name']} atteint une profondeur {function['nesting']}",
                }
            )
    findings += _large_classes(source, language)
    return findings
