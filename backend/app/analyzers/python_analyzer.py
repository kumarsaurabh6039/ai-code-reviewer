"""Python AST analyzer: bugs, code smells, complexity, N+1-ish performance patterns, docstrings."""
import ast

from ..utils.file_utils import FileInfo
from .base import Finding

BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
DB_CALLS = {"execute", "executemany", "fetchone", "fetchall", "query", "find_one"}
HTTP_OBJS = {"requests", "httpx"}
HTTP_CALLS = {"get", "post", "put", "delete", "patch"}

LONG_FUNC = 60
COMPLEXITY_MEDIUM = 12
COMPLEXITY_HIGH = 25
MAX_DEPTH = 4
MAX_ARGS = 7
LARGE_CLASS_METHODS = 20


def complexity(node: ast.AST) -> int:
    c = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.Assert)):
            c += 1
        elif isinstance(n, ast.BoolOp):
            c += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            c += 1 + len(n.ifs)
    return c


def nesting_depth(node: ast.AST, d: int = 0) -> int:
    best = d
    for child in ast.iter_child_nodes(node):
        if isinstance(child, BLOCKS):
            is_elif = (isinstance(node, ast.If) and isinstance(child, ast.If)
                       and len(node.orelse) == 1 and node.orelse[0] is child)
            best = max(best, nesting_depth(child, d if is_elif else d + 1))
        else:
            best = max(best, nesting_depth(child, d))
    return best


def _func_len(fn) -> int:
    """Body length only: excludes the signature and the docstring."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return 0
    return (getattr(fn, "end_lineno", None) or body[-1].lineno) - body[0].lineno + 1


def analyze_python(fi: FileInfo) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    stats = {"functions": 0, "classes": 0, "public_functions": 0, "documented": 0}
    try:
        tree = ast.parse(fi.content)
    except SyntaxError as e:
        if fi.non_production:
            return [], stats
        findings.append(Finding(fi.rel_path, e.lineno or 1, "medium", "bug", "Syntax error",
                                f"File could not be parsed as Python 3: {e.msg}.",
                                "Fix the syntax, or exclude the file if it is Python 2 or a template.",
                                "PY-SYNTAX", confidence=0.7))
        return findings, stats

    quiet = fi.non_production  # still count stats, but do not report style/quality findings
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            stats["classes"] += 1
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > LARGE_CLASS_METHODS:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "low", "code_smell", f"Large class '{node.name}'",
                    f"The class has {len(methods)} methods, which suggests it carries too many responsibilities.",
                    "Split it into smaller, focused classes or services (Single Responsibility Principle).",
                    "PY-LARGE-CLASS", node.end_lineno, 0.7))

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stats["functions"] += 1
            if not node.name.startswith("_"):
                stats["public_functions"] += 1
                if ast.get_docstring(node):
                    stats["documented"] += 1
            n_lines = _func_len(node)
            if n_lines > LONG_FUNC:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "medium" if n_lines < 150 else "high", "code_smell",
                    f"Long function '{node.name}' ({n_lines} lines)",
                    "Long functions are hard to read, test and maintain.",
                    "Break the function into small, well-named helper functions.",
                    "PY-LONG-FUNC", node.end_lineno, 0.85))
            cx = complexity(node)
            if cx >= COMPLEXITY_MEDIUM:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "high" if cx >= COMPLEXITY_HIGH else "medium", "code_smell",
                    f"High cyclomatic complexity in '{node.name}' ({cx})",
                    "Too many branches and conditions make bugs easy to hide and the function hard to test.",
                    "Use early returns and move conditions into helper functions or lookup tables.",
                    "PY-COMPLEXITY", node.end_lineno, 0.85))
            depth = nesting_depth(node)
            if depth > MAX_DEPTH:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "low", "code_smell", f"Deep nesting in '{node.name}' (depth {depth})",
                    "Deeply nested if/for/try blocks make code hard to follow.",
                    "Use guard clauses (early returns) and helper functions.",
                    "PY-NESTING", node.end_lineno, 0.8))
            a = node.args
            n_args = len(a.args) + len(a.kwonlyargs) + len(getattr(a, "posonlyargs", []))
            if n_args > MAX_ARGS:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "low", "code_smell", f"Too many parameters in '{node.name}' ({n_args})",
                    "Many parameters make a function hard to call and hard to change.",
                    "Group related parameters into a dataclass or pydantic model.",
                    "PY-MANY-ARGS", confidence=0.7))
            defaults = list(a.defaults) + [d for d in a.kw_defaults if d is not None]
            for d in defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)) or (
                        isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id in {"list", "dict", "set"}):
                    findings.append(Finding(
                        fi.rel_path, node.lineno, "medium", "bug", f"Mutable default argument in '{node.name}'",
                        "A mutable default value is shared across all calls, causing surprising state bugs.",
                        "Default to None and create a fresh object inside the function.",
                        "PY-MUTABLE-DEFAULT", confidence=0.95,
                        fix_before=f"def {node.name}(items=[]):",
                        fix_after=f"def {node.name}(items=None):\n    items = [] if items is None else items"))
                    break

        elif isinstance(node, ast.ExceptHandler):
            only_pass = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
            if node.type is None:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "medium", "bug", "Bare 'except:' clause",
                    "A bare except also catches KeyboardInterrupt/SystemExit and hides real errors.",
                    "Catch specific exception types and log the error.", "PY-BARE-EXCEPT", confidence=0.95,
                    fix_before="except:\n    pass", fix_after="except ValueError as exc:\n    logger.exception(exc)"))
            elif only_pass:
                findings.append(Finding(
                    fi.rel_path, node.lineno, "low", "bug", "Exception silently swallowed",
                    "The exception is caught and ignored, which makes failures hard to debug.",
                    "At least log the error, or handle it properly.", "PY-SWALLOWED", confidence=0.8))

        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call) or not isinstance(sub.func, ast.Attribute):
                    continue
                attr = sub.func.attr
                is_db = attr in DB_CALLS
                is_http = (attr in HTTP_CALLS and isinstance(sub.func.value, ast.Name)
                           and sub.func.value.id in HTTP_OBJS)
                if is_db or is_http:
                    kind = "HTTP request" if is_http else "database call"
                    findings.append(Finding(
                        fi.rel_path, sub.lineno, "medium", "performance", f"Possible N+1: {kind} inside a loop",
                        f"A {kind} runs on every loop iteration, which gets very slow as data grows.",
                        "Fetch the data before the loop with one batch query or bulk request (JOIN, IN clause, eager loading).",
                        "PY-N-PLUS-ONE", confidence=0.6))
                    break

    # unreachable code after return/raise/continue/break
    for node in ast.walk(tree):
        for fld in ("body", "orelse", "finalbody"):
            stmts = getattr(node, fld, None)
            if isinstance(stmts, list):
                for i, st in enumerate(stmts[:-1]):
                    if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)) and isinstance(stmts[i + 1], ast.stmt):
                        findings.append(Finding(
                            fi.rel_path, stmts[i + 1].lineno, "low", "bug", "Unreachable code",
                            "Code after return/raise/continue/break never runs.",
                            "Remove the dead code or fix the logic error.", "PY-UNREACHABLE", confidence=0.9))
                        break

    if quiet:
        return [], stats
    if stats["public_functions"] >= 5 and stats["documented"] / stats["public_functions"] < 0.3:
        findings.append(Finding(
            fi.rel_path, 1, "low", "documentation", "Most public functions have no docstrings",
            f"Only {stats['documented']} of {stats['public_functions']} public functions are documented.",
            "Add short docstrings to public functions (purpose, arguments, return value).",
            "PY-DOCSTRINGS", confidence=0.7))
    return findings, stats
