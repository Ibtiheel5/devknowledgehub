import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Node

from app.code_intelligence.parsers.tree_sitter_parser import (
    LanguageSpec,
    TreeSitterParser,
    _descendants,
    _text,
)

_JS_LANGUAGE = Language(tsjavascript.language())


def _call_name(node: Node, src: bytes) -> str:
    if node.type == "new_expression":
        return _text(node.child_by_field_name("constructor"), src)
    return _text(node.child_by_field_name("function"), src)


def _import_name(node: Node, src: bytes) -> tuple[str, list[str]]:
    source = node.child_by_field_name("source")
    if source is None:
        return "", []
    module = _text(source, src).strip("'\"")
    names = [
        _text(n.child_by_field_name("name"), src)
        for n in _descendants(node, {"import_specifier"})
    ]
    return module, [n for n in names if n]


def _bases(node: Node, src: bytes) -> list[str]:
    bases: list[str] = []
    for heritage in (c for c in node.children if c.type == "class_heritage"):
        bases += [
            _text(n, src)
            for n in _descendants(heritage, {"identifier", "type_identifier"})
        ]
    return list(dict.fromkeys(b for b in bases if b))


SPEC = LanguageSpec(
    name="javascript",
    language=_JS_LANGUAGE,
    class_nodes=frozenset({"class_declaration"}),
    method_nodes=frozenset({"method_definition"}),
    function_nodes=frozenset(
        {"function_declaration", "generator_function_declaration"}
    ),
    field_nodes=frozenset({"field_definition", "public_field_definition"}),
    import_nodes=frozenset({"import_statement"}),
    call_nodes=frozenset({"call_expression", "new_expression"}),
    call_name=_call_name,
    import_name=_import_name,
    bases=_bases,
)


class JavaScriptParser(TreeSitterParser):
    def __init__(self) -> None:
        super().__init__(SPEC)
