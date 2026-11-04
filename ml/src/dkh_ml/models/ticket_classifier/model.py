from pathlib import Path

from dkh_ml.models.text_classifier import TextClassifier

LABELS = ("BUG", "FEATURE", "TECHNICAL_DEBT")
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "ticket_classifier.joblib"


def ticket_text(row: dict) -> str:
    title = str(row.get("title") or "").strip()
    description = str(row.get("description") or "").strip()
    return f"{title}\n{description}".strip()


class TicketClassifier:
    """Classifie un ticket en BUG / FEATURE / TECHNICAL_DEBT."""

    def __init__(self, *, max_features: int = 20_000, c: float = 1.0):
        self.model = TextClassifier(max_features=max_features, c=c)

    def fit(self, rows: list[dict]) -> "TicketClassifier":
        self.model.fit([ticket_text(r) for r in rows], [str(r["label"]) for r in rows])
        return self

    def predict(self, rows: list[dict]) -> list[str]:
        return self.model.predict([ticket_text(r) for r in rows])

    def predict_ticket(self, title: str, description: str | None = None) -> dict:
        row = {"title": title, "description": description}
        label = self.model.predict([ticket_text(row)])[0]
        probabilities = self.model.predict_proba([ticket_text(row)])[0]
        return {"label": label, "confidence": probabilities.get(label, 0.0), "probabilities": probabilities}

    def save(self, path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model.save(path)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL_PATH) -> "TicketClassifier":
        instance = cls()
        instance.model = TextClassifier.load(path)
        return instance
