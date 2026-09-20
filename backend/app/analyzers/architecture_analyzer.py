"""Architecture heuristics: circular imports (Python), data-access in controllers, god files."""
import ast
import re
from pathlib import PurePosixPath

from ..utils.file_utils import FileInfo
from .base import Finding

CONTROLLER_HINTS = {"api", "routes", "route", "routers", "controllers", "controller", "views", "endpoints", "handlers"}
DB_HINTS = re.compile(r"\b(session|db|cursor|conn|connection)\.(query|execute|add|commit|scalars|fetchall)\(|"
                      r"\.objects\.(filter|get|all|create)\(|\bSELECT\s.+\sFROM\b", re.I)


def _module_name(rel: str) -> str:
    p = PurePosixPath(rel)
    parts = list(p.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_candidates(f: FileInfo) -> set[str]:
    """Dotted module names this file imports (relative imports resolved)."""
    try:
        tree = ast.parse(f.content)
    except SyntaxError:
        return set()
    parts = list(PurePosixPath(f.rel_path).with_suffix("").parts)
    package = parts[:-1]
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = package[: max(0, len(package) - (node.level - 1))] if node.level else []
            full = base + (node.module.split(".") if node.module else [])
            if full:
                out.add(".".join(full))
            for a in node.names:
                out.add(".".join(full + [a.name]))
    return out


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles, seen = [], set()
    color: dict[str, int] = {}

    def dfs(node, stack):
        color[node] = 1
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            if color.get(nxt, 0) == 0:
                dfs(nxt, stack)
            elif color.get(nxt) == 1:
                cyc = stack[stack.index(nxt):]
                key = frozenset(cyc)
                if key not in seen and len(cyc) > 1:
                    seen.add(key)
                    cycles.append(cyc + [nxt])
        stack.pop()
        color[node] = 2

    for n in sorted(graph):
        if color.get(n, 0) == 0:
            dfs(n, [])
    return cycles


def analyze_architecture(files: list[FileInfo]) -> list[Finding]:
    findings: list[Finding] = []
    py = [f for f in files if f.language == "Python" and not f.non_production]

    # --- circular imports (Python only, AST based) ---
    known = {_module_name(f.rel_path): f.rel_path for f in py if PurePosixPath(f.rel_path).name != "__init__.py"}
    graph: dict[str, set[str]] = {m: set() for m in known}
    for f in py:
        if PurePosixPath(f.rel_path).name == "__init__.py":
            continue
        me = _module_name(f.rel_path)
        for cand in _import_candidates(f):
            for k in known:
                if k != me and (k == cand or k.endswith("." + cand)):
                    graph[me].add(k)
    for cyc in _find_cycles(graph)[:5]:
        first = known[cyc[0]]
        findings.append(Finding(
            first, 1, "medium", "architecture", "Circular dependency between modules",
            "Import cycle detected: " + " -> ".join(cyc) + ". Cycles cause import errors and tight coupling.",
            "Extract shared code into a third module, or use dependency inversion / lazy imports.",
            "ARCH-CIRCULAR", confidence=0.65))

    # --- data access inside controllers ---
    for f in files:
        if f.language not in {"Python", "JavaScript", "TypeScript"} or f.non_production:
            continue
        parts = {p.lower() for p in PurePosixPath(f.rel_path).parts[:-1]} | {PurePosixPath(f.rel_path).stem.lower()}
        if parts & CONTROLLER_HINTS:
            hits = [i for i, ln in enumerate(f.content.splitlines(), 1) if DB_HINTS.search(ln)]
            if len(hits) >= 3:
                findings.append(Finding(
                    f.rel_path, hits[0], "medium", "architecture", "Data access logic inside controller/route file",
                    f"{len(hits)} direct database calls found in a route/controller layer. Business and data logic mixed "
                    "with HTTP handling is hard to test and reuse.",
                    "Move queries and business rules into a service/repository layer; keep routes thin.",
                    "ARCH-LAYER", confidence=0.6))

    # --- god files ---
    for f in files:
        if f.language in {"Python", "JavaScript", "TypeScript"} and not f.non_production and f.lines > 900:
            findings.append(Finding(
                f.rel_path, 1, "medium", "architecture", f"Oversized module ({f.lines} lines)",
                "A very large module usually mixes several responsibilities.",
                "Split by responsibility into cohesive modules.", "ARCH-GOD-FILE", confidence=0.7))
    return findings
