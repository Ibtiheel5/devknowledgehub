"""Écritures complémentaires du graphe : commits, docs, tickets, technologies, findings."""
from app.graph.schema import (
    commit_id,
    documentation_id,
    file_id,
    finding_id,
    issue_id,
    technology_id,
)
from app.services.content_service import extract_mentions


def add_commit(driver, repo_name: str, commit: dict | None, file_paths: list[str]) -> None:
    if not commit or not commit.get("sha"):
        return
    cid = commit_id(repo_name, commit["sha"])
    with driver.session() as session:
        session.run(
            """
            MATCH (r:Repository {name: $repo})
            MERGE (c:Commit {id: $id})
            SET c.sha = $sha, c.message = $message, c.author = $author,
                c.committed_at = $committed_at
            MERGE (r)-[:HAS_COMMIT]->(c)
            """,
            repo=repo_name,
            id=cid,
            sha=commit["sha"],
            message=commit.get("message"),
            author=commit.get("author"),
            committed_at=commit.get("committed_at"),
        )
        if file_paths:
            session.run(
                """
                MATCH (c:Commit {id: $id})
                UNWIND $file_ids AS fid
                MATCH (f:File {id: fid})
                MERGE (c)-[:SNAPSHOT_OF]->(f)
                """,
                id=cid,
                file_ids=[file_id(repo_name, p) for p in file_paths],
            )


def add_technologies(driver, repo_name: str, technologies: list[dict]) -> None:
    if not technologies:
        return
    rows = [
        {
            "id": technology_id(t["name"]),
            "name": t["name"],
            "category": t.get("category"),
            "version": t.get("version"),
        }
        for t in technologies
    ]
    with driver.session() as session:
        session.run(
            """
            MATCH (r:Repository {name: $repo})
            UNWIND $rows AS row
            MERGE (t:Technology {id: row.id})
            SET t.name = row.name, t.category = row.category, t.version = row.version
            MERGE (r)-[:USES]->(t)
            """,
            repo=repo_name,
            rows=rows,
        )


def add_documents(
    driver,
    repo_name: str,
    documents: list[dict],
    *,
    file_paths: list[str],
    symbol_ids: dict[str, str],
) -> None:
    if not documents:
        return
    rows = []
    for doc in documents:
        mentioned_files, mentioned_symbols = extract_mentions(
            doc["content"], file_paths, list(symbol_ids)
        )
        rows.append(
            {
                "id": documentation_id(repo_name, doc["path"]),
                "path": doc["path"],
                "title": doc.get("title"),
                "kind": doc.get("kind"),
                "files": [file_id(repo_name, p) for p in mentioned_files],
                "symbols": [symbol_ids[s] for s in mentioned_symbols if s in symbol_ids],
            }
        )
    with driver.session() as session:
        session.run(
            """
            MATCH (r:Repository {name: $repo})
            UNWIND $rows AS row
            MERGE (d:Documentation {id: row.id})
            SET d.path = row.path, d.title = row.title, d.kind = row.kind
            MERGE (r)-[:HAS_DOCUMENTATION]->(d)
            """,
            repo=repo_name,
            rows=rows,
        )
        session.run(
            """
            UNWIND $rows AS row
            MATCH (d:Documentation {id: row.id})
            UNWIND row.files AS fid
            MATCH (f:File {id: fid})
            MERGE (d)-[:DOCUMENTS]->(f)
            """,
            rows=rows,
        )
        session.run(
            """
            UNWIND $rows AS row
            MATCH (d:Documentation {id: row.id})
            UNWIND row.symbols AS sid
            MATCH (s:Symbol {id: sid})
            MERGE (d)-[:DESCRIBES]->(s)
            """,
            rows=rows,
        )


def issue_graph_row(
    repo_name: str,
    issue: dict,
    file_paths: list[str],
    symbol_ids: dict[str, str],
) -> dict:
    mentioned_files, mentioned_symbols = extract_mentions(
        f"{issue['title']} {issue.get('description') or ''}", file_paths, list(symbol_ids)
    )
    external = issue.get("external_id") or f"db-{issue['id']}"
    return {
        "id": issue_id(repo_name, str(external)),
        "external_id": issue.get("external_id"),
        "title": issue["title"],
        "kind": issue.get("kind"),
        "status": issue.get("status"),
        "files": [file_id(repo_name, p) for p in mentioned_files],
        "symbols": [symbol_ids[s] for s in mentioned_symbols if s in symbol_ids],
    }


def add_issues(driver, repo_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with driver.session() as session:
        session.run(
            """
            MATCH (r:Repository {name: $repo})
            UNWIND $rows AS row
            MERGE (i:Issue {id: row.id})
            SET i.external_id = row.external_id, i.title = row.title,
                i.kind = row.kind, i.status = row.status
            MERGE (r)-[:HAS_ISSUE]->(i)
            """,
            repo=repo_name,
            rows=rows,
        )
        session.run(
            """
            UNWIND $rows AS row
            MATCH (i:Issue {id: row.id})
            UNWIND row.files AS fid
            MATCH (f:File {id: fid})
            MERGE (i)-[:AFFECTS]->(f)
            """,
            rows=rows,
        )
        session.run(
            """
            UNWIND $rows AS row
            MATCH (i:Issue {id: row.id})
            UNWIND row.symbols AS sid
            MATCH (s:Symbol {id: sid})
            MERGE (i)-[:MENTIONS]->(s)
            """,
            rows=rows,
        )


def add_findings(driver, repo_name: str, findings: list[dict]) -> None:
    if not findings:
        return
    for finding in findings:
        model = (finding.get("model_name") or "").lower()
        if "vuln" in model:
            label = "Vulnerability"
        elif "smell" in model or "debt" in model:
            label = "CodeSmell"
        else:
            label = "Finding"
        fid = finding_id(
            repo_name,
            finding.get("model_name") or "unknown",
            str(finding.get("target_id") or finding.get("id")),
        )
        with driver.session() as session:
            session.run(
                f"""
                MATCH (r:Repository {{name: $repo}})
                MERGE (n:{label} {{id: $id}})
                SET n.label = $label, n.score = $score, n.model = $model,
                    n.file = $file, n.symbol = $symbol
                MERGE (r)-[:HAS_FINDING]->(n)
                """,
                repo=repo_name,
                id=fid,
                label=finding.get("label"),
                score=finding.get("score"),
                model=finding.get("model_name"),
                file=finding.get("file"),
                symbol=finding.get("symbol"),
            )
            if finding.get("symbol"):
                session.run(
                    """
                    MATCH (n {id: $id})
                    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(:File)
                          -[:DEFINES]->(s:Symbol {qualified_name: $symbol})
                    MERGE (s)-[:HAS_FINDING]->(n)
                    """,
                    id=fid,
                    repo=repo_name,
                    symbol=finding["symbol"],
                )
            elif finding.get("file"):
                session.run(
                    """
                    MATCH (n {id: $id})
                    MATCH (f:File {id: $file_id})
                    MERGE (f)-[:HAS_FINDING]->(n)
                    """,
                    id=fid,
                    file_id=file_id(repo_name, finding["file"]),
                )
