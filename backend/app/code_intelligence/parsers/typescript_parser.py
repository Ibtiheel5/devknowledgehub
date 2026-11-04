import tree_sitter_typescript as tstypescript
from tree_sitter import Language

from app.code_intelligence.parsers.javascript_parser import (
    _bases,
    _call_name,
    _import_name,
)
from app.code_intelligence.parsers.tree_sitter_parser import LanguageSpec, TreeSitterParser

_TS_LANGUAGE = Language(tstypescript.language_typescript())
_TSX_LANGUAGE = Language(tstypescript.language_tsx())

_CLASS_NODES = frozenset(
    {
        "class_declaration",
        "abstract_class_declaration",
        "interface_declaration",
        "enum_declaration",
    }
)


def _spec(name: str, language: Language) -> LanguageSpec:
    return LanguageSpec(
        name=name,
        language=language,
        class_nodes=_CLASS_NODES,
        method_nodes=frozenset({"method_definition", "method_signature"}),
        function_nodes=frozenset(
            {"function_declaration", "generator_function_declaration"}
        ),
        field_nodes=frozenset(
            {"public_field_definition", "field_definition", "property_signature"}
        ),
        import_nodes=frozenset({"import_statement"}),
        call_nodes=frozenset({"call_expression", "new_expression"}),
        call_name=_call_name,
        import_name=_import_name,
        bases=_bases,
    )


class TypeScriptParser(TreeSitterParser):
    def __init__(self) -> None:
        super().__init__(_spec("typescript", _TS_LANGUAGE))


class TsxParser(TreeSitterParser):
    def __init__(self) -> None:
        super().__init__(_spec("tsx", _TSX_LANGUAGE))
