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
    (
        "CREATE CONSTRAINT dkh_commit_id IF NOT EXISTS "
        "FOR (c:Commit) REQUIRE c.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_issue_id IF NOT EXISTS "
        "FOR (i:Issue) REQUIRE i.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_doc_id IF NOT EXISTS "
        "FOR (d:Documentation) REQUIRE d.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_technology_id IF NOT EXISTS "
        "FOR (t:Technology) REQUIRE t.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_finding_id IF NOT EXISTS "
        "FOR (f:Finding) REQUIRE f.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_smell_id IF NOT EXISTS "
        "FOR (f:CodeSmell) REQUIRE f.id IS UNIQUE"
    ),
    (
        "CREATE CONSTRAINT dkh_vulnerability_id IF NOT EXISTS "
        "FOR (f:Vulnerability) REQUIRE f.id IS UNIQUE"
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


def commit_id(repo: str, sha: str) -> str:
    return f"{repo}::commit::{sha}"


def issue_id(repo: str, external_id: str) -> str:
    return f"{repo}::issue::{external_id}"


def documentation_id(repo: str, path: str) -> str:
    return f"{repo}::doc::{path}"


def technology_id(name: str) -> str:
    return f"tech::{name.lower()}"


def finding_id(repo: str, model_name: str, target_id: str) -> str:
    return f"{repo}::finding::{model_name}::{target_id}"
