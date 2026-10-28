from app.graph.resolution import resolve_calls_for_file
from app.graph.schema import file_id, module_id, symbol_id
from app.schemas.code import RepositoryAnalysis


class GraphBuilder:
    """Construit le knowledge graph d'un dépôt dans Neo4j, par lots (UNWIND)."""

    def __init__(self, driver):
        self._driver = driver

    def build(self, analysis: RepositoryAnalysis, repo_name: str) -> dict:
        files, symbols, parent_links, imports, calls = self._prepare_rows(analysis, repo_name)

        with self._driver.session() as session:
            session.run(
                "MERGE (r:Repository {name: $name}) SET r.root = $root",
                name=repo_name,
                root=analysis.root,
            )
            session.run(
                """
                UNWIND $rows AS row
                MERGE (f:File {id: row.id})
                SET f.path = row.path, f.language = row.language
                WITH f, row
                MATCH (r:Repository {name: $repo_name})
                MERGE (r)-[:CONTAINS]->(f)
                """,
                rows=files,
                repo_name=repo_name,
            )
            session.run(
                """
                UNWIND $rows AS row
                MERGE (s:Symbol {id: row.id})
                SET s.kind = row.kind, s.name = row.name,
                    s.qualified_name = row.qualified_name,
                    s.start_line = row.start_line, s.end_line = row.end_line
                WITH s, row
                MATCH (f:File {id: row.file_id})
                MERGE (f)-[:DEFINES]->(s)
                """,
                rows=symbols,
            )
            if parent_links:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (parent:Symbol {id: row.parent_id})
                    MATCH (child:Symbol {id: row.child_id})
                    MERGE (parent)-[:PARENT_OF]->(child)
                    """,
                    rows=parent_links,
                )
            if imports:
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (m:Module {id: row.id})
                    SET m.name = row.name
                    WITH m, row
                    MATCH (f:File {id: row.file_id})
                    MERGE (f)-[:IMPORTS]->(m)
                    """,
                    rows=imports,
                )
            if calls:
                session.run(
                    """
                    UNWIND $rows AS row
                    MATCH (caller:Symbol {id: row.caller_id})
                    MATCH (callee:Symbol {id: row.callee_id})
                    MERGE (caller)-[:CALLS {line: row.line}]->(callee)
                    """,
                    rows=calls,
                )

        return {
            "files": len(files),
            "symbols": len(symbols),
            "imports": len(imports),
            "calls_resolved": len(calls),
            "calls_unresolved": sum(len(f.calls) for f in analysis.files) - len(calls),
        }

    def _prepare_rows(self, analysis: RepositoryAnalysis, repo_name: str):
        files, symbols, parent_links, imports, calls = [], [], [], [], []
        symbol_ids_by_qn: dict[str, str] = {}

        for f in analysis.files:
            fid = file_id(repo_name, f.path)
            files.append({"id": fid, "path": f.path, "language": f.language})

            for s in f.symbols:
                sid = symbol_id(repo_name, f.path, s.qualified_name)
                symbol_ids_by_qn[(f.path, s.qualified_name)] = sid
                symbols.append(
                    {
                        "id": sid,
                        "file_id": fid,
                        "kind": s.kind,
                        "name": s.name,
                        "qualified_name": s.qualified_name,
                        "start_line": s.start_line,
                        "end_line": s.end_line,
                    }
                )
                if s.parent:
                    parent_links.append(
                        {
                            "parent_id": symbol_ids_by_qn.get((f.path, s.parent)),
                            "child_id": sid,
                        }
                    )

            for i in f.imports:
                imports.append(
                    {"id": module_id(repo_name, i.module), "name": i.module, "file_id": fid}
                )

            for caller_qn, callee_qn, line in resolve_calls_for_file(f):
                caller_id = symbol_ids_by_qn.get((f.path, caller_qn))
                callee_id = symbol_ids_by_qn.get((f.path, callee_qn))
                if caller_id and callee_id:
                    calls.append({"caller_id": caller_id, "callee_id": callee_id, "line": line})

        parent_links = [p for p in parent_links if p["parent_id"]]
        return files, symbols, parent_links, imports, calls
