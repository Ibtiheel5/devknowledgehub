from app.code_intelligence.parsers.python_parser import PythonParser
from app.graph.resolution import resolve_calls_for_file

SAMPLE = '''\
def top():
    helper()
    os.path.join("a", "b")


class AuthService:
    def login(self, user):
        return self.check(user)

    def check(self, user):
        def inner():
            return len(user)
        return inner()
'''


def test_resolves_local_calls_and_drops_external():
    analysis = PythonParser().parse(SAMPLE, "auth.py")
    resolved = {(caller, callee) for caller, callee, _line in resolve_calls_for_file(analysis)}

    assert ("top", "helper") not in resolved  # helper() est appelée mais non définie ici : externe
    assert ("AuthService.login", "AuthService.check") in resolved
    assert ("AuthService.check", "AuthService.check.inner") in resolved
    # os.path.join et len ne sont jamais définis dans ce fichier : non résolus
    assert not any(callee in ("os.path.join", "len") for _, callee in resolved)
