from app.code_intelligence.parsers.python_parser import PythonParser

SAMPLE = '''\
import os
import numpy as np
from app.utils import helper, other as o
from x import *


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


def parse():
    return PythonParser().parse(SAMPLE, "auth.py")


def test_symbols_kinds_and_lines():
    r = parse()
    by_name = {s.qualified_name: s for s in r.symbols}
    assert by_name["top"].kind == "function"
    assert by_name["AuthService"].kind == "class"
    assert by_name["AuthService.login"].kind == "method"
    assert by_name["AuthService.login"].parent == "AuthService"
    assert by_name["AuthService.check.inner"].kind == "function"
    assert by_name["top"].start_line == 7


def test_imports():
    r = parse()
    mods = {i.module: i for i in r.imports}
    assert {"os", "numpy", "app.utils", "x"} <= set(mods)
    assert mods["app.utils"].names == ["helper", "other"]
    assert mods["x"].names == ["*"]


def test_calls_have_caller_and_line():
    r = parse()
    calls = {(c.caller, c.callee) for c in r.calls}
    assert ("top", "helper") in calls
    assert ("top", "os.path.join") in calls
    assert ("AuthService.login", "self.check") in calls
    assert ("AuthService.check", "inner") in calls
    assert ("AuthService.check.inner", "len") in calls
