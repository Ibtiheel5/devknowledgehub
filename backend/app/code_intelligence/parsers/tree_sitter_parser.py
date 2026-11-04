"""Parser générique piloté par une spécification de langage Tree-sitter.

Chaque langage fournit la liste des nœuds qui représentent des classes, méthodes,
fonctions, champs, imports et appels. Le parcours reste volontairement simple :
il produit des symboles qualifiés (Classe.methode, fonction.locale, ...) avec
leurs lignes, ce qui suffit au chunking et au knowledge graph.
"""
from collections.abc import Callable
from dataclasses import dataclass

from tree_sitter import Language, Node, Parser

from app.schemas.code import CallRef, FileAnalysis, ImportRef, Symbol


def _text(node: Node | None, src: bytes) -> str:
    if node is None:
        return ""
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _descendants(node: Node, types: set[str]) -> list[Node]:
    out: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type in types:
            out.append(current)
        stack.extend(reversed(current.children))
    return out


def clean_import(text: str) -> str:
    return text.replace("import", "").replace("static", "").strip().rstrip(";").strip()


@dataclass(frozen=True)
class LanguageSpec:
    name: str
    language: Language
    class_nodes: frozenset[str]
    method_nodes: frozenset[str]
    function_nodes: frozenset[str]
    field_nodes: frozenset[str]
    import_nodes: frozenset[str]
    call_nodes: frozenset[str]
    call_name: Callable[[Node, bytes], str]
    import_name: Callable[[Node, bytes], tuple[str, list[str]]]
    bases: Callable[[Node, bytes], list[str]]


class TreeSitterParser:
    def __init__(self, spec: LanguageSpec) -> None:
        self.spec = spec
        self.language = spec.name
        self._parser = Parser(spec.language)

    def parse(self, source: str, file_path: str) -> FileAnalysis:
        src = source.encode("utf-8")
        tree = self._parser.parse(src)
        result = FileAnalysis(
            path=file_path, language=self.language, lines=source.count("\n") + 1
        )
        self._walk(tree.root_node, src, file_path, result, [], [])
        return result

    def _walk(self, node, src, file, out, class_stack, func_stack) -> None:
        t = node.type

        if t in self.spec.class_nodes:
            name = _text(node.child_by_field_name("name"), src)
            if name:
                qualified = ".".join([*class_stack, name])
                out.symbols.append(
                    Symbol(
                        kind="class",
                        name=name,
                        qualified_name=qualified,
                        file=file,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=".".join(class_stack) or None,
                        bases=self.spec.bases(node, src),
                    )
                )
                for child in node.children:
                    self._walk(child, src, file, out, [*class_stack, name], func_stack)
                return

        if t in self.spec.method_nodes or t in self.spec.function_nodes:
            name = _text(node.child_by_field_name("name"), src)
            if name:
                in_class = bool(class_stack) and not func_stack
                kind = "method" if in_class else "function"
                qualified = ".".join([*class_stack, *func_stack, name])
                out.symbols.append(
                    Symbol(
                        kind=kind,
                        name=name,
                        qualified_name=qualified,
                        file=file,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=".".join(class_stack) if in_class else None,
                    )
                )
                for child in node.children:
                    self._walk(child, src, file, out, class_stack, [*func_stack, name])
                return

        if t == "variable_declarator":
            value = node.child_by_field_name("value")
            name = _text(node.child_by_field_name("name"), src)
            if name and value is not None and value.type in {
                "arrow_function",
                "function_expression",
                "function",
            }:
                in_class = bool(class_stack) and not func_stack
                kind = "method" if in_class else "function"
                qualified = ".".join([*class_stack, *func_stack, name])
                out.symbols.append(
                    Symbol(
                        kind=kind,
                        name=name,
                        qualified_name=qualified,
                        file=file,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=".".join(class_stack) if in_class else None,
                    )
                )
                self._walk(value, src, file, out, class_stack, [*func_stack, name])
                return

        if t in self.spec.field_nodes:
            names: list[str] = []
            direct = node.child_by_field_name("name")
            if direct is not None:
                names.append(_text(direct, src))
            else:
                for child in node.children:
                    if child.type == "variable_declarator":
                        declared = child.child_by_field_name("name")
                        if declared is not None:
                            names.append(_text(declared, src))
            parent = ".".join(class_stack) or None
            for name in names:
                if not name:
                    continue
                out.symbols.append(
                    Symbol(
                        kind="field",
                        name=name,
                        qualified_name=".".join([*class_stack, name]),
                        file=file,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent=parent,
                    )
                )

        elif t in self.spec.import_nodes:
            module, names = self.spec.import_name(node, src)
            if module:
                out.imports.append(
                    ImportRef(file=file, module=module, names=names, line=node.start_point[0] + 1)
                )

        elif t in self.spec.call_nodes:
            callee = self.spec.call_name(node, src)
            if callee:
                caller = ".".join([*class_stack, *func_stack]) or "<module>"
                out.calls.append(
                    CallRef(
                        file=file,
                        caller=caller,
                        callee=callee,
                        line=node.start_point[0] + 1,
                    )
                )

        for child in node.children:
            self._walk(child, src, file, out, class_stack, func_stack)
