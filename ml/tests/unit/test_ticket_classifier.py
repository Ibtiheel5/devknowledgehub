from pathlib import Path

from dkh_ml.common.io import read_jsonl, train_test_split
from dkh_ml.evaluation.metrics import classification_report
from dkh_ml.models.ticket_classifier import TicketClassifier

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tickets.jsonl"


def test_ticket_classifier_learns_fixture():
    rows = read_jsonl(FIXTURE)
    train, test = train_test_split(rows, test_size=0.2, seed=7, label_key="label")
    model = TicketClassifier().fit(train)
    report = classification_report(
        [r["label"] for r in test], model.predict(test), labels=["BUG", "FEATURE", "TECHNICAL_DEBT"]
    )
    assert report["accuracy"] >= 0.8
    assert report["macro_f1"] >= 0.75


def test_ticket_classifier_roundtrip(tmp_path):
    rows = read_jsonl(FIXTURE)
    model = TicketClassifier().fit(rows)
    path = tmp_path / "ticket.joblib"
    model.save(path)

    loaded = TicketClassifier.load(path)
    sample = [{"title": "Application crashes with error", "description": "NullPointerException"}]
    assert loaded.predict(sample) == model.predict(sample)
    result = loaded.predict_ticket("Application crashes with error", "NullPointerException")
    assert result["label"] in {"BUG", "FEATURE", "TECHNICAL_DEBT"}
    assert 0.0 <= result["confidence"] <= 1.0
