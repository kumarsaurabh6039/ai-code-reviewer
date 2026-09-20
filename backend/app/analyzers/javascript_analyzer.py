"""Lightweight regex-based checks for JS/TS (no external parser needed)."""
import re

from ..utils.file_utils import FileInfo
from .base import Finding

EMPTY_CATCH = re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}")
FUNC_RE = re.compile(r"\bfunction\b|=>|\bclass\s+\w+|\b(constructor|async)\b")
ANY_RE = re.compile(r":\s*any\b|<any>|\bas any\b")


def analyze_javascript(fi: FileInfo) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    text = fi.content
    lines = text.splitlines()
    stats = {"functions": len(re.findall(r"\bfunction\b|=>", text)), "classes": len(re.findall(r"\bclass\s+\w+", text))}

    if fi.non_production:
        return [], stats
    if fi.lines > 600:
        findings.append(Finding(fi.rel_path, 1, "low", "code_smell", f"Very large file ({fi.lines} lines)",
                                "Very large files are hard to understand and maintain.",
                                "Split the file into smaller modules or components.", "JS-LARGE-FILE", confidence=0.7))
    logs = [i + 1 for i, ln in enumerate(lines) if re.search(r"\bconsole\.(log|debug)\(", ln)]
    if len(logs) > 8 and not fi.is_test:
        findings.append(Finding(fi.rel_path, logs[0], "low", "code_smell", f"{len(logs)} console.log statements",
                                "Debug logging seems to have been left in production code.",
                                "Use a proper logger or remove the debug logs.", "JS-CONSOLE-LOG", confidence=0.7))
    for m in EMPTY_CATCH.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        findings.append(Finding(fi.rel_path, line, "medium", "bug", "Empty catch block",
                                "The error is caught and ignored, so failures stay hidden.",
                                "Log the error, show it to the user, or rethrow it.", "JS-EMPTY-CATCH",
                                confidence=0.9))
    if fi.language == "TypeScript":
        any_count = len(ANY_RE.findall(text))
        if any_count > 10:
            findings.append(Finding(fi.rel_path, 1, "low", "code_smell", f"Heavy use of 'any' ({any_count} times)",
                                    "'any' removes the type-safety benefits of TypeScript.",
                                    "Define proper interfaces/types (or use 'unknown' with type guards).",
                                    "TS-ANY", confidence=0.7))
    var_count = len(re.findall(r"^\s*var\s+\w+", text, re.M))
    if var_count > 5:
        findings.append(Finding(fi.rel_path, 1, "low", "code_smell", f"'var' used {var_count} times",
                                "'var' is function-scoped and causes hoisting bugs.",
                                "Use 'const' / 'let'.", "JS-VAR", confidence=0.7))
    return findings, stats
