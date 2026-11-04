from pathlib import Path

from dkh_ml.models.text_classifier import TextClassifier

DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "project_classifier.joblib"

PROJECT_TYPES = ("application", "library", "service", "full-stack")


def project_text(row: dict) -> str:
    files = row.get("files") or []
    languages = row.get("languages") or []
    parts = [
        str(row.get("name") or ""),
        str(row.get("readme") or ""),
        " ".join(str(f) for f in files),
        " ".join(str(lang) for lang in languages),
    ]
    return "\n".join(part for part in parts if part).strip()


class ProjectClassifier:
    """Détecte le type de projet (application, library, service, full-stack)."""

    def __init__(self, *, max_features: int = 30_000, c: float = 1.0):
        self.model = TextClassifier(max_features=max_features, c=c)

    def fit(self, rows: list[dict]) -> "ProjectClassifier":
        self.model.fit([project_text(r) for r in rows], [str(r["project_type"]) for r in rows])
        return self

    def predict(self, rows: list[dict]) -> list[str]:
        return self.model.predict([project_text(r) for r in rows])

    def predict_project(self, row: dict) -> dict:
        probabilities = self.model.predict_proba([project_text(row)])[0]
        label = max(probabilities, key=probabilities.get)
        return {"project_type": label, "confidence": probabilities[label], "probabilities": probabilities}

    def save(self, path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model.save(path)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MODEL_PATH) -> "ProjectClassifier":
        instance = cls()
        instance.model = TextClassifier.load(path)
        return instance
