"""Test coverage heuristics based on file naming (no code is executed)."""
from pathlib import PurePosixPath

from ..utils.file_utils import FileInfo
from .base import Finding

SKIP_NAMES = {"__init__", "conftest", "setup", "manage", "wsgi", "asgi", "settings", "config", "main", "index",
              "app.module", "app.config", "app.routes", "environment"}


def _stem(path: str) -> str:
    n = PurePosixPath(path).name.lower()
    for suf in (".spec.ts", ".test.ts", ".spec.js", ".test.js", ".spec.tsx", ".test.tsx", ".py", ".ts", ".js", ".tsx", ".jsx"):
        if n.endswith(suf):
            n = n[: -len(suf)]
            break
    return n.removeprefix("test_").removesuffix("_test")


def analyze_testing(files: list[FileInfo]) -> tuple[list[Finding], dict]:
    tests = [f for f in files if f.is_test and f.language in {"Python", "JavaScript", "TypeScript"}]
    source = [f for f in files if f.is_logic and _stem(f.rel_path) not in SKIP_NAMES
              and "migrations" not in f.rel_path.lower() and f.loc >= 15]
    tested = {_stem(t.rel_path) for t in tests}
    untested = [f for f in source if _stem(f.rel_path) not in tested]
    stats = {"test_files": len(tests), "source_files": len(source), "untested_modules": len(untested)}
    findings: list[Finding] = []

    if source and not tests:
        biggest = max(source, key=lambda f: f.loc)
        findings.append(Finding(
            biggest.rel_path, 1, "high", "testing", "No automated tests found",
            f"The project has {len(source)} source modules but no test files (test_*.py, *.spec.ts, tests/ ...).",
            "Start with tests for the most critical modules (authentication, payments, data access).",
            "TEST-NONE", confidence=0.85))
    elif untested and len(untested) >= 3:
        ranked = sorted(untested, key=lambda f: -f.loc)[:5]
        names = ", ".join(f.rel_path for f in ranked)
        findings.append(Finding(
            ranked[0].rel_path, 1, "medium", "testing", f"{len(untested)} modules have no matching test file",
            f"Largest untested modules: {names}.",
            "Add unit tests for these modules, starting with the ones holding business logic.",
            "TEST-UNTESTED", confidence=0.6))
    return findings, stats
