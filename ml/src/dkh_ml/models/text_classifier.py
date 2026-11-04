"""Baseline texte réutilisable : TF-IDF + régression logistique."""
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


class TextClassifier:
    def __init__(self, *, max_features: int = 20_000, ngram_max: int = 2, c: float = 1.0):
        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, ngram_max),
                        min_df=1,
                        max_features=max_features,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        C=c,
                    ),
                ),
            ]
        )

    def fit(self, texts: list[str], labels: list[str]) -> "TextClassifier":
        self.pipeline.fit(texts, labels)
        return self

    def predict(self, texts: list[str]) -> list[str]:
        return [str(label) for label in self.pipeline.predict(texts)]

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        probabilities = self.pipeline.predict_proba(texts)
        classes = [str(c) for c in self.pipeline.classes_]
        return [
            {label: round(float(score), 4) for label, score in zip(classes, row, strict=True)}
            for row in probabilities
        ]

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, target)

    @classmethod
    def load(cls, path: str | Path) -> "TextClassifier":
        model = cls()
        model.pipeline = joblib.load(Path(path))
        return model
