"""Résolution best-effort des appels vers un symbole défini dans le même fichier.

Limite connue : ne résout pas les appels vers un autre fichier (ex. une
fonction importée). Ce sera traité dans une phase ultérieure, en s'appuyant
sur le graphe des imports pour désambiguïser.
"""
from app.schemas.code import FileAnalysis


def resolve_calls_for_file(file: FileAnalysis) -> list[tuple[str, str, int]]:
    """Renvoie une liste de (appelant, symbole_appelé, ligne) pour les appels résolus."""
    qualified_names = {s.qualified_name for s in file.symbols}
    resolved: list[tuple[str, str, int]] = []

    for call in file.calls:
        callee = call.callee
        target: str | None = None

        if callee.startswith("self."):
            method = callee[len("self.") :]
            class_name = call.caller.split(".")[0]
            candidate = f"{class_name}.{method}"
            if candidate in qualified_names:
                target = candidate

        elif "." not in callee:
            if callee in qualified_names:
                target = callee
            else:
                suffix = f".{callee}"
                matches = [qn for qn in qualified_names if qn.endswith(suffix)]
                if len(matches) == 1:
                    target = matches[0]

        if target and target != call.caller:
            resolved.append((call.caller, target, call.line))

    return resolved
