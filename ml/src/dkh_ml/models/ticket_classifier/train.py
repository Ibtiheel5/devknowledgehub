"""Entraîne et évalue le classifieur de tickets (baseline TF-IDF + LR)."""
import argparse
import json

from dkh_ml.common.io import read_jsonl, train_test_split, write_json
from dkh_ml.common.tracking import log_to_mlflow
from dkh_ml.evaluation.metrics import classification_report
from dkh_ml.models.ticket_classifier.model import DEFAULT_MODEL_PATH, LABELS, TicketClassifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="JSONL avec title/description/label")
    parser.add_argument("--model", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metrics", default="reports/ticket_metrics.json")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mlflow", action="store_true")
    args = parser.parse_args()

    rows = read_jsonl(args.data)
    train, test = train_test_split(rows, test_size=args.test_size, seed=args.seed, label_key="label")
    model = TicketClassifier().fit(train)

    predictions = model.predict(test)
    truth = [str(r["label"]) for r in test]
    report = classification_report(truth, predictions, labels=list(LABELS))
    report["split"] = {"train": len(train), "test": len(test), "seed": args.seed}
    write_json(args.metrics, report)
    model.save(args.model)
    print(json.dumps(report, indent=2))

    if args.mlflow:
        log_to_mlflow(
            "ticket_classifier",
            params={"test_size": args.test_size, "seed": args.seed, "model": "tfidf+logreg"},
            metrics={k: report[k] for k in ("accuracy", "macro_f1", "weighted_f1")},
            artifacts=[args.model, args.metrics],
            tags={"task": "ticket_classification"},
        )


if __name__ == "__main__":
    main()
