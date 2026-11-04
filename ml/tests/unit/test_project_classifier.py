from pathlib import Path

from dkh_ml.common.io import read_jsonl, train_test_split
from dkh_ml.evaluation.metrics import classification_report
from dkh_ml.models.project_classifier import PROJECT_TYPES, ProjectClassifier

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "projects.jsonl"


def test_project_classifier_learns_fixture():
    rows = read_jsonl(FIXTURE)
    train, test = train_test_split(rows, test_size=0.25, seed=3, label_key="project_type")
    model = ProjectClassifier().fit(train)
    report = classification_report(
        [r["project_type"] for r in test], model.predict(test), labels=list(PROJECT_TYPES)
    )
    assert report["accuracy"] >= 0.75


def test_project_predict_returns_probabilities():
    model = ProjectClassifier().fit(read_jsonl(FIXTURE))
    result = model.predict_project(
        {
            "name": "react-fastapi-app",
            "readme": "Full stack app with React frontend and FastAPI backend",
            "files": ["frontend/package.json", "backend/main.py"],
        }
    )
    assert result["project_type"] in PROJECT_TYPES
    assert abs(sum(result["probabilities"].values()) - 1.0) < 0.01
