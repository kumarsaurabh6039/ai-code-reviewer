"""Detects copy-pasted blocks by hashing sliding windows of normalized lines."""
import hashlib
import re
from collections import defaultdict

from ..utils.file_utils import FileInfo
from .base import Finding

WINDOW = 8
MAX_FINDINGS = 12
DUP_LANGS = {"Python", "JavaScript", "TypeScript", "SQL"}


def _normalize(fi: FileInfo) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(fi.content.splitlines(), start=1):
        s = re.sub(r"\s+", " ", line.strip())
        if len(s) < 12 or s.startswith(("#", "//", "*", "/*", "import ", "from ", "export ", "})", "});")):
            continue
        out.append((i, s))
    return out


def analyze_duplicates(files: list[FileInfo]) -> list[Finding]:
    index: dict[str, list[tuple[str, int]]] = defaultdict(list)
    norm: dict[str, list[tuple[int, str]]] = {}
    for fi in files:
        if fi.language not in DUP_LANGS or fi.non_production or fi.lines > 3000:
            continue
        lines = _normalize(fi)
        norm[fi.rel_path] = lines
        for k in range(len(lines) - WINDOW + 1):
            h = hashlib.md5("\n".join(s for _, s in lines[k:k + WINDOW]).encode()).hexdigest()  # noqa: S324 (not security)
            index[h].append((fi.rel_path, k))

    dup_marks: dict[str, dict[int, tuple[str, int]]] = defaultdict(dict)  # file -> idx -> other location
    for h, locs in index.items():
        if len(locs) < 2 or len(locs) > 6:
            continue
        for path, k in locs:
            other = next(((p, kk) for p, kk in locs if (p, kk) != (path, k)), None)
            if other:
                for d in range(WINDOW):
                    dup_marks[path].setdefault(k + d, other)

    findings: list[Finding] = []
    for path, marks in dup_marks.items():
        lines = norm[path]
        idxs = sorted(marks)
        start = prev = idxs[0]
        for idx in idxs[1:] + [None]:
            if idx is not None and idx == prev + 1:
                prev = idx
                continue
            length = prev - start + 1
            if length >= WINDOW:
                other_path, other_k = marks[start]
                first_line, last_line = lines[start][0], lines[prev][0]
                other_line = norm[other_path][other_k][0]
                findings.append(Finding(
                    path, first_line, "medium" if length >= 20 else "low", "duplication",
                    f"Duplicated code block (~{length} lines)",
                    f"Lines {first_line}-{last_line} closely match code in {other_path} (around line {other_line}).",
                    "Extract the shared logic into one function/module and reuse it.",
                    "DUP-BLOCK", last_line, 0.75))
            if idx is not None:
                start = prev = idx
    findings.sort(key=lambda f: -(f.end_line or f.line) + f.line)
    return findings[:MAX_FINDINGS]
