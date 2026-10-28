"""Analyse un dépôt local ou une URL git et affiche un résumé.

Usage :
    python scripts/analyze_repo.py /chemin/vers/depot
    python scripts/analyze_repo.py https://github.com/pallets/click
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.code_intelligence.symbol_extractor import analyze_directory  # noqa: E402
from app.services.ingestion_service import clone_repository  # noqa: E402


def report(analysis) -> None:
    print(f"Langages      : {analysis.languages}")
    print(f"Fichiers Python parsés : {len(analysis.files)}")
    print(f"Symboles      : {analysis.symbol_count}")
    print(f"Imports       : {sum(len(f.imports) for f in analysis.files)}")
    print(f"Appels        : {sum(len(f.calls) for f in analysis.files)}")
    print("\nExemples de symboles :")
    shown = 0
    for f in analysis.files:
        for s in f.symbols:
            print(f"  {s.kind:8} {s.qualified_name:40} {s.file}:{s.start_line}")
            shown += 1
            if shown >= 10:
                return


if __name__ == "__main__":
    target = sys.argv[1]
    if target.startswith("https://"):
        with clone_repository(target) as path:
            report(analyze_directory(path))
    else:
        report(analyze_directory(Path(target)))
