from dkh_ml.evaluation.metrics import (
    classification_report,
    confusion_matrix,
    mrr,
    ndcg_at_k,
    recall_at_k,
    retrieval_report,
)


def test_classification_report_perfect_predictions():
    report = classification_report(["BUG", "FEATURE", "BUG"], ["BUG", "FEATURE", "BUG"])
    assert report["accuracy"] == 1.0
    assert report["macro_f1"] == 1.0
    assert report["per_class"]["BUG"]["support"] == 2


def test_classification_report_partial():
    report = classification_report(["BUG", "BUG", "FEATURE"], ["BUG", "FEATURE", "FEATURE"])
    assert report["accuracy"] == round(2 / 3, 4)
    assert report["per_class"]["BUG"]["recall"] == 0.5
    assert report["per_class"]["FEATURE"]["precision"] == 0.5


def test_confusion_matrix_shape():
    matrix = confusion_matrix(["A", "B"], ["B", "B"], labels=["A", "B"])
    assert matrix["matrix"] == [[0, 1], [0, 1]]


def test_retrieval_metrics():
    relevant = {"a", "c"}
    retrieved = ["b", "a", "c"]
    assert recall_at_k(relevant, retrieved, 2) == 0.5
    assert recall_at_k(relevant, retrieved, 3) == 1.0
    assert mrr(relevant, retrieved) == 0.5
    assert 0 < ndcg_at_k(relevant, retrieved, 3) <= 1.0


def test_retrieval_report_aggregates():
    report = retrieval_report(
        [
            {"relevant": ["a"], "retrieved": ["a", "b"]},
            {"relevant": ["c"], "retrieved": ["b", "c"]},
        ],
        k=2,
    )
    assert report["recall_at_k"] == 1.0
    assert report["mrr"] == 0.75
    assert report["n_queries"] == 2
