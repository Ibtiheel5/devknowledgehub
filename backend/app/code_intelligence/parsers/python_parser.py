import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from app.schemas.code import CallRef, FileAnalysis, ImportRef, Symbol

_PY_LANGUAGE = Language(tspython.language())


def _text(node: Node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


class PythonParser:
    language = "python"

    def __init__(self) -> None:
        self._parser = Parser(_PY_LANGUAGE)

    def parse(self, source: str, file_path: str) -> FileAnalysis:
        src = source.encode("utf-8")
        tree = self._parser.parse(src)
        result = FileAnalysis(
            path=file_path, language=self.language, lines=source.count("\n") + 1
        )
        self._walk(tree.root_node, src, file_path, result, class_stack=[], func_stack=[])
        return result

    # -- parcours récursif -------------------------------------------------
    def _walk(self, node, src, file, out, class_stack, func_stack):
        t = node.type

        if t == "class_definition":
            name = _text(node.child_by_field_name("name"), src)
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
                )
            )
            for child in node.children:
                self._walk(child, src, file, out, [*class_stack, name], func_stack)
            return

        if t == "function_definition":
            name = _text(node.child_by_field_name("name"), src)
            in_class = bool(class_stack) and not func_stack
            qualified = ".".join([*class_stack, *func_stack, name])
            out.symbols.append(
                Symbol(
                    kind="method" if in_class else "function",
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

        if t == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    out.imports.append(
                        ImportRef(file=file, module=_text(child, src), line=node.start_point[0] + 1)
                    )
                elif child.type == "aliased_import":
                    name_node = child.child_by_field_name("name")
                    out.imports.append(
                        ImportRef(
                            file=file, module=_text(name_node, src), line=node.start_point[0] + 1
                        )
                    )
            return

        if t == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            module = _text(module_node, src) if module_node else ""
            names = []
            for child in node.children_by_field_name("name"):
                if child.type == "aliased_import":
                    names.append(_text(child.child_by_field_name("name"), src))
                else:
                    names.append(_text(child, src))
            if any(c.type == "wildcard_import" for c in node.children):
                names.append("*")
            out.imports.append(
                ImportRef(file=file, module=module, names=names, line=node.start_point[0] + 1)
            )
            return

        if t == "call":
            fn = node.child_by_field_name("function")
            if fn is not None:
                caller = ".".join([*class_stack, *func_stack]) or "<module>"
                out.calls.append(
                    CallRef(
                        file=file,
                        caller=caller,
                        callee=_text(fn, src),
                        line=node.start_point[0] + 1,
                    )
                )

        for child in node.children:
            self._walk(child, src, file, out, class_stack, func_stack)
