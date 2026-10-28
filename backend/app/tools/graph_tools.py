"""Outils (tools) exposés aux agents : fine couche au-dessus des requêtes Neo4j."""
from app.graph import queries


class GraphTools:
    def __init__(self, driver, repo_name: str):
        self.driver = driver
        self.repo = repo_name

    def search_symbols(self, term: str, limit: int = 20) -> list[dict]:
        return queries.search_symbols(self.driver, self.repo, term, limit)

    def callers(self, qualified_name: str) -> list[dict]:
        return queries.get_callers(self.driver, self.repo, qualified_name)

    def callees(self, qualified_name: str) -> list[dict]:
        return queries.get_callees(self.driver, self.repo, qualified_name)

    def overview(self) -> dict:
        extra = queries.get_repo_overview(self.driver, self.repo)
        return {
            "stats": queries.get_repo_stats(self.driver, self.repo),
            "symbols": queries.get_repo_symbols(self.driver, self.repo, 8),
            "files": extra["files"],
            "modules": extra["modules"],
        }
