import argparse
from pathlib import Path

from app.code_intelligence.symbol_extractor import analyze_directory
from app.db.neo4j_client import get_driver
from app.graph.builder import GraphBuilder
from app.graph.schema import apply_constraints


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a local Python project into Neo4j.")
    parser.add_argument("path", nargs="?", default="app", help="Folder to analyze")
    parser.add_argument("--repo-name", default="devknowledgehub-backend")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    analysis = analyze_directory(target)

    driver = get_driver()
    apply_constraints(driver)
    counts = GraphBuilder(driver).build(analysis, args.repo_name)

    print(f"Indexed {target}")
    print(counts)


if __name__ == "__main__":
    main()
