"""Métriques de classification et de retrieval (implémentation stdlib, testable)."""
from collections import Counter


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def per_class_metrics(
    y_true: list[str], y_pred: list[str], labels: list[str] | None = None
) -> dict[str, dict]:
    labels = labels or sorted(set(y_true) | set(y_pred))
    report: dict[str, dict] = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        report[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    return report


def confusion_matrix(
    y_true: list[str], y_pred: list[str], labels: list[str] | None = None
) -> dict:
    labels = labels or sorted(set(y_true) | set(y_pred))
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for truth, pred in zip(y_true, y_pred, strict=True):
        if truth in index and pred in index:
            matrix[index[truth]][index[pred]] += 1
    return {"labels": labels, "matrix": matrix}


def classification_report(
    y_true: list[str], y_pred: list[str], labels: list[str] | None = None
) -> dict:
    labels = labels or sorted(set(y_true) | set(y_pred))
    per_class = per_class_metrics(y_true, y_pred, labels)
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(per_class) if per_class else 0.0
    total = sum(m["support"] for m in per_class.values()) or 1
    weighted_f1 = sum(m["f1"] * m["support"] for m in per_class.values()) / total
    accuracy = _safe_div(sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p), len(y_true))
    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels),
        "n_samples": len(y_true),
        "label_distribution": dict(Counter(y_true)),
    }


def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(relevant & set(retrieved[:k])) / len(relevant)


def mrr(relevant: set[str], retrieved: list[str]) -> float:
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    dcg = sum(1.0 / _log2(rank + 1) for rank, item in enumerate(retrieved[:k], start=1)
              if item in relevant)
    ideal = sum(1.0 / _log2(rank + 1) for rank in range(1, min(len(relevant), k) + 1))
    return _safe_div(dcg, ideal)


def _log2(value: float) -> float:
    import math

    return math.log2(value)


def retrieval_report(
    queries: list[dict], *, k: int = 5
) -> dict:
    """`queries` : [{"relevant": [ids], "retrieved": [ids]}, ...]."""
    if not queries:
        return {"recall_at_k": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0, "n_queries": 0}
    n = len(queries)
    return {
        "recall_at_k": round(sum(recall_at_k(set(q["relevant"]), q["retrieved"], k) for q in queries) / n, 4),
        "mrr": round(sum(mrr(set(q["relevant"]), q["retrieved"]) for q in queries) / n, 4),
        "ndcg_at_k": round(sum(ndcg_at_k(set(q["relevant"]), q["retrieved"], k) for q in queries) / n, 4),
        "n_queries": n,
        "k": k,
    }
