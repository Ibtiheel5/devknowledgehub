from dkh_ml.models.clone_detector import (
    evaluate,
    is_clone,
    lexical_similarity,
    similarity,
    token_jaccard,
)

CODE_A = "def add(a, b):\n    return a + b\n"
CODE_B = "def add(x, y):\n    return x + y\n"
CODE_C = "class Report:\n    def render(self):\n        return '<html></html>'\n"


def test_identical_code_is_clone():
    assert lexical_similarity(CODE_A, CODE_A) == 1.0
    assert token_jaccard(CODE_A, CODE_A) == 1.0
    assert is_clone(CODE_A, CODE_A)


def test_renamed_clone_detected():
    assert similarity(CODE_A, CODE_B) > 0.75
    assert is_clone(CODE_A, CODE_B)


def test_unrelated_code_not_clone():
    assert similarity(CODE_A, CODE_C) < 0.75
    assert not is_clone(CODE_A, CODE_C)


def test_evaluate_returns_report():
    report = evaluate(
        [
            {"code_a": CODE_A, "code_b": CODE_B, "label": "CLONE"},
            {"code_a": CODE_A, "code_b": CODE_C, "label": "DIFFERENT"},
        ]
    )
    assert report["accuracy"] == 1.0
    assert report["n_pairs"] == 2
