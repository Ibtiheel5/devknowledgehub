def get_callers(driver, repo_name: str, qualified_name: str) -> list[dict]:
    query = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(:File)-[:DEFINES]->(target:Symbol {qualified_name: $qn})
    MATCH (caller:Symbol)-[c:CALLS]->(target)
    RETURN caller.qualified_name AS qualified_name, caller.kind AS kind, c.line AS line
    ORDER BY qualified_name
    """
    with driver.session() as session:
        result = session.run(query, repo=repo_name, qn=qualified_name)
        return [dict(record) for record in result]


def get_callees(driver, repo_name: str, qualified_name: str) -> list[dict]:
    query = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(:File)-[:DEFINES]->(caller:Symbol {qualified_name: $qn})
    MATCH (caller)-[c:CALLS]->(callee:Symbol)
    RETURN callee.qualified_name AS qualified_name, callee.kind AS kind, c.line AS line
    ORDER BY qualified_name
    """
    with driver.session() as session:
        result = session.run(query, repo=repo_name, qn=qualified_name)
        return [dict(record) for record in result]


def get_repo_stats(driver, repo_name: str) -> dict:
    query = """
    MATCH (r:Repository {name: $repo})
    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
    OPTIONAL MATCH (f)-[:DEFINES]->(s:Symbol)
    OPTIONAL MATCH (f)-[i:IMPORTS]->(m:Module)
    OPTIONAL MATCH (s)-[c:CALLS]->(:Symbol)
    RETURN count(DISTINCT f) AS files,
           count(DISTINCT s) AS symbols,
           count(DISTINCT m) AS modules,
           count(DISTINCT i) AS imports,
           count(DISTINCT c) AS calls
    """
    with driver.session() as session:
        record = session.run(query, repo=repo_name).single()
        return (
            dict(record)
            if record
            else {"files": 0, "symbols": 0, "modules": 0, "imports": 0, "calls": 0}
        )


def get_repo_calls(driver, repo_name: str, limit: int = 50) -> list[dict]:
    query = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(caller_file:File)-[:DEFINES]->(caller:Symbol)
    MATCH (caller)-[call:CALLS]->(callee:Symbol)
    OPTIONAL MATCH (callee_file:File)-[:DEFINES]->(callee)
    RETURN caller.qualified_name AS caller,
           caller.kind AS caller_kind,
           caller_file.path AS caller_file,
           callee.qualified_name AS callee,
           callee.kind AS callee_kind,
           callee_file.path AS callee_file,
           call.line AS line
    ORDER BY caller, callee, line
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(query, repo=repo_name, limit=limit)
        return [dict(record) for record in result]


def get_repo_symbols(driver, repo_name: str, limit: int = 50) -> list[dict]:
    query = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(f:File)-[:DEFINES]->(s:Symbol)
    OPTIONAL MATCH (s)-[outgoing:CALLS]->(:Symbol)
    WITH f, s, count(outgoing) AS outgoing_calls
    OPTIONAL MATCH (:Symbol)-[incoming:CALLS]->(s)
    RETURN s.qualified_name AS qualified_name,
           s.name AS name,
           s.kind AS kind,
           f.path AS file,
           s.start_line AS start_line,
           s.end_line AS end_line,
           outgoing_calls,
           count(incoming) AS incoming_calls,
           outgoing_calls + count(incoming) AS degree
    ORDER BY degree DESC, qualified_name
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(query, repo=repo_name, limit=limit)
        return [dict(record) for record in result]


def search_symbols(driver, repo_name: str, term: str, limit: int = 20) -> list[dict]:
    """Recherche de symboles par sous-chaîne (insensible à la casse) sur name / qualified_name."""
    query = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(f:File)-[:DEFINES]->(s:Symbol)
    WHERE toLower(s.name) CONTAINS toLower($term)
       OR toLower(s.qualified_name) CONTAINS toLower($term)
    RETURN s.qualified_name AS qualified_name,
           s.name AS name,
           s.kind AS kind,
           f.path AS file,
           s.start_line AS start_line,
           s.end_line AS end_line
    LIMIT $limit
    """
    with driver.session() as session:
        result = session.run(query, repo=repo_name, term=term, limit=limit)
        return [dict(record) for record in result]


def get_repo_overview(driver, repo_name: str, top: int = 8) -> dict:
    """Vue d'ensemble : fichiers les plus riches en symboles et modules les plus importés."""
    files_q = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(f:File)
    OPTIONAL MATCH (f)-[:DEFINES]->(s:Symbol)
    RETURN f.path AS path, f.language AS language, count(s) AS symbols
    ORDER BY symbols DESC, path
    LIMIT $top
    """
    modules_q = """
    MATCH (r:Repository {name: $repo})-[:CONTAINS]->(f:File)-[:IMPORTS]->(m:Module)
    RETURN m.name AS name, count(DISTINCT f) AS files
    ORDER BY files DESC, name
    LIMIT $top
    """
    with driver.session() as session:
        files = [dict(x) for x in session.run(files_q, repo=repo_name, top=top)]
        modules = [dict(x) for x in session.run(modules_q, repo=repo_name, top=top)]
    return {"files": files, "modules": modules}
