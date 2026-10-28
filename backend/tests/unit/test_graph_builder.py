from app.code_intelligence.parsers.python_parser import PythonParser
from app.graph.builder import GraphBuilder
from app.schemas.code import RepositoryAnalysis

SAMPLE = '''\
import os


def top():
    helper()


class AuthService:
    def login(self, user):
        return self.check(user)

    def check(self, user):
        return True
'''


class FakeResult:
    def single(self):
        return None

    def __iter__(self):
        return iter([])


class FakeSession:
    def __init__(self, log):
        self._log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self._log.append((query, params))
        return FakeResult()


class FakeDriver:
    def __init__(self):
        self.log: list[tuple[str, dict]] = []

    def session(self):
        return FakeSession(self.log)


def _analysis() -> RepositoryAnalysis:
    fa = PythonParser().parse(SAMPLE, "auth.py")
    return RepositoryAnalysis(root="/tmp/repo", languages={"python": 1}, files=[fa])


def test_build_sends_expected_batches_to_neo4j():
    driver = FakeDriver()
    counts = GraphBuilder(driver).build(_analysis(), "myrepo")

    assert counts["files"] == 1
    assert counts["symbols"] == 4  # top, AuthService, AuthService.login, AuthService.check
    queries = [q for q, _ in driver.log]
    assert any("MERGE (r:Repository" in q for q in queries)
    assert any("MERGE (f:File" in q for q in queries)
    assert any("MERGE (s:Symbol" in q for q in queries)
    assert any("PARENT_OF" in q for q in queries)
    assert any("MATCH (caller:Symbol" in q for q in queries)  # AuthService.login -> self.check résolu


def test_build_counts_unresolved_calls():
    driver = FakeDriver()
    counts = GraphBuilder(driver).build(_analysis(), "myrepo")
    # "helper()" dans top() n'est jamais défini dans ce fichier -> non résolu
    assert counts["calls_unresolved"] >= 1
