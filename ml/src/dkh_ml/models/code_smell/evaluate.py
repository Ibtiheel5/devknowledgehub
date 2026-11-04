"""Évalue le détecteur de code smells (multi-label, correspondance smell+ligne)."""
import argparse
import json
from collections import defaultdict

from dkh_ml.common.io import read_jsonl, write_json
from dkh_ml.common.tracking import log_to_mlflow
from dkh_ml.models.code_smell.detector import detect_smells


def _keys(findings: list[dict]) -> set[tuple[str, int]]:
    return {(f["smell"], int(f.get("line", 0))) for f in findings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="JSONL code/language/expected")
    parser.add_argument("--metrics", default="reports/code_smell_metrics.json")
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.data)
    per_smell: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for row in rows:
        expected = {(item["smell"], int(item.get("line", 0))) for item in row.get("expected", [])}
        predicted = _keys(detect_smells(str(row["code"]), str(row.get("language", "python"))))
        for smell, _line in expected & predicted:
            per_smell[smell]["tp"] += 1
        for smell, _line in predicted - expected:
            per_smell[smell]["fp"] += 1
        for smell, _line in expected - predicted:
            per_smell[smell]["fn"] += 1

    report: dict = {"smells": {}, "micro": {}}
    totals = {"tp": 0, "fp": 0, "fn": 0}
    for smell, counts in sorted(per_smell.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report["smells"][smell] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
        for key in totals:
            totals[key] += counts[key]

    precision = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 0.0
    recall = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    report["micro"] = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "n_files": len(rows),
    }
    write_json(args.metrics, report)
    print(json.dumps(report, indent=2))

    if args.mlflow:
        log_to_mlflow(
            "code_smell",
            params={"model": "structural-rules"},
            metrics=report["micro"],
            artifacts=[args.metrics],
            tags={"task": "code_smell_detection"},
        )


if __name__ == "__main__":
    main()
