"""Évalue la baseline de détection de clones sur des paires annotées."""
import argparse
import json

from dkh_ml.common.io import read_jsonl, write_json
from dkh_ml.common.tracking import log_to_mlflow
from dkh_ml.models.clone_detector.detector import evaluate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="JSONL code_a/code_b/label")
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--metrics", default="reports/clone_metrics.json")
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()

    report = evaluate(read_jsonl(args.data), threshold=args.threshold)
    write_json(args.metrics, report)
    print(json.dumps(report, indent=2))

    if args.mlflow:
        log_to_mlflow(
            "clone_detector",
            params={"threshold": args.threshold, "model": "lexical+jaccard"},
            metrics={k: report[k] for k in ("accuracy", "macro_f1", "weighted_f1")},
            artifacts=[args.metrics],
            tags={"task": "clone_detection"},
        )


if __name__ == "__main__":
    main()
