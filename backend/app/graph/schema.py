"""Modèle du knowledge graph.

Nœuds :
    Repository {name}
    File       {id, path, language}
    Symbol     {id, kind, name, qualified_name, start_line, end_line}
    Module     {id, name}          # cible d'un import

Relations :
    (Repository)-[:CONTAINS]->(File)
    (File)-[:DEFINES]->(Symbol)
    (Symbol)-[:PARENT_OF]->(Symbol)      # classe -> méthode directe
    (File)-[:IMPORTS]->(Module)
    (Symbol)-[:CALLS {line}]->(Symbol)   # uniquement les appels résolus
"""

CONSTRAINTS = [
    (
        "CREATE CONSTRAINT dkh_repo_name IF NOT EXISTS "
        "FOR (r:Repository) REQUIRE r.name IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_file_id IF NOT EXISTS "
        "FOR (f:File) REQUIRE f.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_symbol_id IF NOT EXISTS "
        "FOR (s:Symbol) REQUIRE s.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_module_id IF NOT EXISTS "
        "FOR (m:Module) REQUIRE m.id IS UNIQUE"
    ),
]


def apply_constraints(driver) -> None:
    with driver.session() as session:
        for stmt in CONSTRAINTS:
            session.run(stmt)


def file_id(repo: str, path: str) -> str:
    return f"{repo}::{path}"


def symbol_id(repo: str, path: str, qualified_name: str) -> str:
    return f"{repo}::{path}::{qualified_name}"


def module_id(repo: str, module: str) -> str:
    return f"{repo}::{module}"
