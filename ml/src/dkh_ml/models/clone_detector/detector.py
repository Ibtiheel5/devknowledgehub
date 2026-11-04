"""Baseline de détection de clones : similarité structurelle + Jaccard de tokens."""
import re
from difflib import SequenceMatcher

from dkh_ml.evaluation.metrics import classification_report

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|\"[^\"]*\"|'[^']*'|[^\sA-Za-z0-9_]")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
KEYWORDS = {
    "and", "as", "async", "await", "break", "case", "catch", "class", "const", "continue",
    "def", "delete", "do", "else", "elif", "except", "export", "extends", "false", "finally",
    "for", "from", "function", "if", "implements", "import", "in", "interface", "is", "lambda",
    "let", "new", "none", "not", "null", "or", "pass", "private", "protected", "public", "raise",
    "return", "static", "super", "switch", "this", "throw", "true", "try", "typeof", "var",
    "void", "while", "with", "yield",
}


def tokens(code: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(code)]


def normalized_tokens(code: str) -> list[str]:
    """Remplace identifiants, nombres et littéraux par des placeholders."""
    normalized: list[str] = []
    for token in TOKEN_RE.findall(code):
        lowered = token.lower()
        if lowered in KEYWORDS:
            normalized.append(lowered)
        elif token.startswith(("'", '"')):
            normalized.append("STR")
        elif token.isdigit():
            normalized.append("NUM")
        elif IDENTIFIER_RE.match(token):
            normalized.append("ID")
        else:
            normalized.append(token)
    return normalized


def lexical_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def structural_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalized_tokens(a), normalized_tokens(b)).ratio()


def token_jaccard(a: str, b: str) -> float:
    left, right = set(tokens(a)), set(tokens(b))
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def similarity(a: str, b: str) -> float:
    """Score combiné (0..1) : structure normalisée + recouvrement lexical."""
    score = 0.7 * structural_similarity(a, b) + 0.3 * token_jaccard(a, b)
    return round(score, 4)


def is_clone(a: str, b: str, threshold: float = 0.75) -> bool:
    return similarity(a, b) >= threshold


def evaluate(pairs: list[dict], threshold: float = 0.75) -> dict:
    truth = [str(row["label"]).upper() for row in pairs]
    predictions = [
        "CLONE" if is_clone(str(row["code_a"]), str(row["code_b"]), threshold) else "DIFFERENT"
        for row in pairs
    ]
    report = classification_report(truth, predictions, labels=["CLONE", "DIFFERENT"])
    report["threshold"] = threshold
    report["n_pairs"] = len(pairs)
    return report
