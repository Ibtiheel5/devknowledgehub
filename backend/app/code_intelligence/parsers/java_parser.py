import tree_sitter_java as tsjava
from tree_sitter import Language, Node

from app.code_intelligence.parsers.tree_sitter_parser import (
    LanguageSpec,
    TreeSitterParser,
    _descendants,
    _text,
    clean_import,
)

_JAVA_LANGUAGE = Language(tsjava.language())


def _call_name(node: Node, src: bytes) -> str:
    if node.type == "object_creation_expression":
        return _text(node.child_by_field_name("type"), src)
    name = _text(node.child_by_field_name("name"), src)
    obj = _text(node.child_by_field_name("object"), src)
    return f"{obj}.{name}" if obj and name else name


def _import_name(node: Node, src: bytes) -> tuple[str, list[str]]:
    return clean_import(_text(node, src)), []


def _bases(node: Node, src: bytes) -> list[str]:
    bases: list[str] = []
    for field in ("superclass", "interfaces"):
        child = node.child_by_field_name(field)
        if child is not None:
            bases += [_text(n, src) for n in _descendants(child, {"type_identifier"})]
    return list(dict.fromkeys(b for b in bases if b))


SPEC = LanguageSpec(
    name="java",
    language=_JAVA_LANGUAGE,
    class_nodes=frozenset(
        {
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        }
    ),
    method_nodes=frozenset({"method_declaration", "constructor_declaration"}),
    function_nodes=frozenset(),
    field_nodes=frozenset({"field_declaration", "constant_declaration"}),
    import_nodes=frozenset({"import_declaration"}),
    call_nodes=frozenset({"method_invocation", "object_creation_expression"}),
    call_name=_call_name,
    import_name=_import_name,
    bases=_bases,
)


class JavaParser(TreeSitterParser):
    def __init__(self) -> None:
        super().__init__(SPEC)
