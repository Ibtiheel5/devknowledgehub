from app.code_intelligence.parsers.java_parser import JavaParser
from app.code_intelligence.parsers.javascript_parser import JavaScriptParser
from app.code_intelligence.parsers.typescript_parser import TsxParser, TypeScriptParser

JAVA = """\
package com.demo;

import java.util.List;
import static java.lang.Math.max;

public class AuthService extends BaseService implements IAuth {
    private final JWTService jwt;

    public AuthService(JWTService jwt) {
        this.jwt = jwt;
    }

    public boolean login(String user) {
        return check(user);
    }

    private boolean check(String user) {
        return jwt.validate(user);
    }
}

interface IAuth {
    void login();
}
"""

JAVASCRIPT = """\
import { helper } from "./util";
import React from "react";

class Auth {
  login(user) { return this.check(user); }
  check(u) { return helper(u); }
}

function top() {
  const f = (x) => helper(x);
  return new Auth().login("x");
}

const g = (a) => a + 1;
"""

TYPESCRIPT = """\
import { JWTService } from "./jwt";

export class AuthService implements IAuth {
  private jwt: JWTService;

  constructor(jwt: JWTService) {
    this.jwt = jwt;
  }

  login(user: string): boolean {
    return this.check(user);
  }

  check(u: string): boolean {
    return this.jwt.validate(u);
  }
}

function top(a: number): number {
  return a + 1;
}

interface IAuth {
  login(user: string): boolean;
}
"""

TSX = """\
import React from "react";

export function App(): JSX.Element {
  return <div onClick={() => helper()}>hi</div>;
}
"""


def _by_qn(result):
    return {s.qualified_name: s for s in result.symbols}


def test_java_symbols_imports_calls_and_inheritance():
    r = JavaParser().parse(JAVA, "AuthService.java")
    by_name = _by_qn(r)

    assert by_name["AuthService"].kind == "class"
    assert by_name["AuthService"].bases == ["BaseService", "IAuth"]
    assert by_name["AuthService.jwt"].kind == "field"
    assert by_name["AuthService.login"].kind == "method"
    assert by_name["AuthService.login"].parent == "AuthService"
    assert by_name["AuthService.check"].parent == "AuthService"
    assert by_name["IAuth"].kind == "class"
    assert by_name["IAuth.login"].kind == "method"

    assert {i.module for i in r.imports} == {
        "java.util.List",
        "java.lang.Math.max",
    }
    calls = {(c.caller, c.callee) for c in r.calls}
    assert ("AuthService.login", "check") in calls
    assert ("AuthService.check", "jwt.validate") in calls


def test_javascript_symbols_and_calls():
    r = JavaScriptParser().parse(JAVASCRIPT, "auth.js")
    by_name = _by_qn(r)

    assert by_name["Auth"].kind == "class"
    assert by_name["Auth.login"].kind == "method"
    assert by_name["top"].kind == "function"
    assert by_name["top.f"].kind == "function"
    assert by_name["g"].kind == "function"

    assert {i.module for i in r.imports} == {"./util", "react"}
    assert [i.names for i in r.imports if i.module == "./util"] == [["helper"]]

    calls = {(c.caller, c.callee) for c in r.calls}
    assert ("Auth.login", "this.check") in calls
    assert ("Auth.check", "helper") in calls
    assert ("top.f", "helper") in calls
    assert ("top", "Auth") in calls


def test_typescript_symbols_interfaces_and_calls():
    r = TypeScriptParser().parse(TYPESCRIPT, "auth.ts")
    by_name = _by_qn(r)

    assert by_name["AuthService"].kind == "class"
    assert by_name["AuthService"].bases == ["IAuth"]
    assert by_name["AuthService.jwt"].kind == "field"
    assert by_name["AuthService.login"].kind == "method"
    assert by_name["IAuth"].kind == "class"
    assert by_name["IAuth.login"].kind == "method"

    assert {i.module for i in r.imports} == {"./jwt"}
    calls = {(c.caller, c.callee) for c in r.calls}
    assert ("AuthService.login", "this.check") in calls
    assert ("AuthService.check", "this.jwt.validate") in calls


def test_tsx_grammar_parse():
    r = TsxParser().parse(TSX, "App.tsx")
    by_name = _by_qn(r)

    assert by_name["App"].kind == "function"
    assert ("App", "helper") in {(c.caller, c.callee) for c in r.calls}
