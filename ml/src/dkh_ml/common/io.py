"""Helpers I/O communs aux scripts ML (JSONL, JSON, splits)."""
import json
import random
from pathlib import Path


def read_jsonl(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: str | Path, data: dict | list) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def train_test_split(
    rows: list[dict],
    *,
    test_size: float = 0.2,
    seed: int = 42,
    label_key: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Split déterministe, stratifié par label si possible (sans dépendance sklearn)."""
    rng = random.Random(seed)
    if label_key is None:
        shuffled = list(rows)
        rng.shuffle(shuffled)
        cut = max(1, int(len(shuffled) * (1 - test_size)))
        return shuffled[:cut], shuffled[cut:]

    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(str(row.get(label_key, "UNKNOWN")), []).append(row)

    train: list[dict] = []
    test: list[dict] = []
    for group in groups.values():
        shuffled = list(group)
        rng.shuffle(shuffled)
        n_test = max(1, round(len(shuffled) * test_size)) if len(shuffled) > 1 else 0
        test += shuffled[:n_test]
        train += shuffled[n_test:]

    if not train or not test:
        shuffled = list(rows)
        rng.shuffle(shuffled)
        cut = max(1, int(len(shuffled) * (1 - test_size)))
        return shuffled[:cut], shuffled[cut:]
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test
