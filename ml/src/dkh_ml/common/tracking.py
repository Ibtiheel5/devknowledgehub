"""Intégration MLflow optionnelle : le code fonctionne sans mlflow installé."""
from pathlib import Path


def log_to_mlflow(
    run_name: str,
    *,
    params: dict,
    metrics: dict,
    artifacts: list[str | Path] | None = None,
    tags: dict | None = None,
    experiment: str = "devknowledgehub",
) -> bool:
    try:
        import mlflow
    except ImportError:
        return False

    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({k: str(v) for k, v in params.items()})
        mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
        if tags:
            mlflow.set_tags(tags)
        for artifact in artifacts or []:
            path = Path(artifact)
            if path.exists():
                mlflow.log_artifact(str(path))
    return True
