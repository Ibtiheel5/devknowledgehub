"""Entraîne le classifieur de type de projet à partir de README + structure."""
import argparse
import json

from dkh_ml.common.io import read_jsonl, train_test_split, write_json
from dkh_ml.common.tracking import log_to_mlflow
from dkh_ml.evaluation.metrics import classification_report
from dkh_ml.models.project_classifier.model import (
    DEFAULT_MODEL_PATH,
    PROJECT_TYPES,
    ProjectClassifier,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metrics", default="reports/project_metrics.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.data)
    train, test = train_test_split(
        rows, test_size=args.test_size, seed=args.seed, label_key="project_type"
    )
    model = ProjectClassifier().fit(train)
    predictions = model.predict(test)
    truth = [str(r["project_type"]) for r in test]
    report = classification_report(truth, predictions, labels=list(PROJECT_TYPES))
    report["split"] = {"train": len(train), "test": len(test), "seed": args.seed}
    write_json(args.metrics, report)
    model.save(args.model)
    print(json.dumps(report, indent=2))

    if args.mlflow:
        log_to_mlflow(
            "project_classifier",
            params={"test_size": args.test_size, "seed": args.seed, "model": "tfidf+logreg"},
            metrics={k: report[k] for k in ("accuracy", "macro_f1", "weighted_f1")},
            artifacts=[args.model, args.metrics],
            tags={"task": "project_classification"},
        )


if __name__ == "__main__":
    main()
