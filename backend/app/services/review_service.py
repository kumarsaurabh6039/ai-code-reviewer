"""LLM review layer: runs ONLY on the riskiest files, validates every answer against the real code,
and builds the improvement roadmap."""
import logging
import re
from concurrent.futures import ThreadPoolExecutor

from ..ai.llm import LLMClient
from ..ai.prompts import REVIEW_SYSTEM, ROADMAP_SYSTEM
from ..analyzers.base import CATEGORIES, SEVERITIES, SEVERITY_RANK, Finding
from ..core.config import settings
from ..utils.file_utils import FileInfo

log = logging.getLogger("review")
RISK_WORDS = ("auth", "login", "token", "password", "payment", "billing", "db", "database", "model", "route",
              "api", "view", "controller", "security", "admin", "upload", "user", "session", "service")
SEV_POINTS = {"critical": 8, "high": 5, "medium": 2, "low": 1}
CATEGORY_PRIORITY = {"security": 0, "bug": 1, "performance": 2, "architecture": 3, "testing": 4,
                     "code_smell": 5, "duplication": 6, "documentation": 7}
DEFAULT_EFFORT = {"security": "Low", "bug": "Low", "code_smell": "Medium", "duplication": "Medium",
                  "performance": "Medium", "architecture": "High", "testing": "Medium", "documentation": "Low"}


def pick_files(files: list[FileInfo], findings: list[Finding], limit: int) -> list[FileInfo]:
    score: dict[str, float] = {}
    for f in findings:
        score[f.file_path] = score.get(f.file_path, 0) + SEV_POINTS.get(f.severity, 1)
    ranked = []
    for fi in files:
        if fi.language not in {"Python", "JavaScript", "TypeScript", "SQL"} or fi.is_test or fi.loc < 10:
            continue
        s = score.get(fi.rel_path, 0)
        name = fi.rel_path.lower()
        s += 3 * sum(1 for w in RISK_WORDS if w in name)
        s += min(fi.loc, 400) / 200
        ranked.append((s, fi))
    ranked.sort(key=lambda t: -t[0])
    return [fi for _, fi in ranked[:limit]]


def _numbered(fi: FileInfo) -> str:
    out, size = [], 0
    for i, line in enumerate(fi.content.splitlines(), start=1):
        row = f"{i}: {line[:300]}"
        size += len(row) + 1
        if size > settings.llm_max_chars_per_file:
            out.append(f"... (truncated at line {i})")
            break
        out.append(row)
    return "\n".join(out).replace("</file>", "</ file>")


def _validate(item: dict, fi: FileInfo) -> Finding | None:
    try:
        line = int(item.get("line"))
    except (TypeError, ValueError):
        return None
    if not (1 <= line <= max(fi.lines, 1)):
        return None  # hallucinated line number
    sev, cat = str(item.get("severity", "")).lower(), str(item.get("category", "")).lower()
    if sev not in SEVERITIES or cat not in CATEGORIES:
        return None
    title = str(item.get("title", "")).strip()[:200]
    desc = str(item.get("description", "")).strip()[:1200]
    if not title or not desc:
        return None
    end = item.get("end_line")
    try:
        end = int(end) if end else None
        if end is not None and not (line <= end <= fi.lines):
            end = None
    except (TypeError, ValueError):
        end = None
    try:
        conf = float(item.get("confidence", 0.7))
    except (TypeError, ValueError):
        conf = 0.7
    # never trust a critical AI finding fully: cap severity if confidence is low
    if sev == "critical" and conf < 0.6:
        sev = "high"
    return Finding(fi.rel_path, line, sev, cat, title, desc, str(item.get("suggestion", ""))[:1000], "AI-REVIEW",
                   end, max(0.0, min(1.0, conf)), str(item.get("fix_before", ""))[:1200],
                   str(item.get("fix_after", ""))[:1200], "ai")


def _review_one(llm: LLMClient, fi: FileInfo, static: list[Finding]) -> list[Finding]:
    known = "\n".join(f"- line {f.line}: {f.title}" for f in static if f.file_path == fi.rel_path) or "(none)"
    user = (f"Language: {fi.language}\nAlready detected (do not repeat):\n{known}\n\n"
            f'<file path="{fi.rel_path}">\n{_numbered(fi)}\n</file>')
    data = llm.complete_json(REVIEW_SYSTEM, user, max_tokens=2500)
    if not data or not isinstance(data.get("issues"), list):
        return []
    result = []
    for item in data["issues"][:8]:
        if isinstance(item, dict):
            f = _validate(item, fi)
            if f:
                result.append(f)
    return result


def ai_review(llm: LLMClient, files: list[FileInfo], static: list[Finding], on_progress=None) -> list[Finding]:
    chosen = pick_files(files, static, settings.llm_max_files)
    if not chosen:
        return []
    found: list[Finding] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for n, res in enumerate(pool.map(lambda fi: _review_one(llm, fi, static), chosen), start=1):
            found += res
            if on_progress:
                on_progress(f"AI review {n}/{len(chosen)} files")
    # drop AI findings that duplicate a static one (same file, nearby line, same category)
    unique = []
    for f in found:
        if any(s.file_path == f.file_path and s.category == f.category and abs(s.line - f.line) <= 3 for s in static):
            continue
        if any(u.file_path == f.file_path and u.line == f.line and u.title == f.title for u in unique):
            continue
        unique.append(f)
    return unique


# ---------------- roadmap ----------------
def deterministic_roadmap(issues: list[dict], limit: int = 8) -> list[dict]:
    """issues: dicts with id, severity, category, title, rule_id, description."""
    groups: dict[tuple, list[dict]] = {}
    for i in issues:
        key = (i.get("rule_id") if i.get("rule_id") not in (None, "", "AI-REVIEW") else i["title"], i["category"])
        groups.setdefault(key, []).append(i)
    items = []
    for (_, cat), grp in groups.items():
        worst = min(grp, key=lambda g: SEVERITY_RANK[g["severity"]])
        title = re.sub(r"\s+in\s+'[^']*'|\s*'[^']*'|\s*\(.*?\)", "", worst["title"]).strip() or worst["title"]
        effort = DEFAULT_EFFORT.get(cat, "Medium")
        if len(grp) > 6 and effort == "Low":
            effort = "Medium"
        items.append({"rank": (SEVERITY_RANK[worst["severity"]], CATEGORY_PRIORITY.get(cat, 9), -len(grp)), "title": f"Fix: {title}" + (f" ({len(grp)} places)" if len(grp) > 1 else ""),
                      "category": cat, "effort": effort, "issue_ids": [g["id"] for g in grp][:15],
                      "why": worst["description"][:200]})
    items.sort(key=lambda x: x["rank"])
    out = []
    for n, it in enumerate(items[:limit], start=1):
        it.pop("rank")
        out.append({"priority": n, **it})
    return out


def build_roadmap(llm: LLMClient, issues: list[dict]) -> tuple[list[dict], str | None]:
    base = deterministic_roadmap(issues)
    if not issues or not llm.available:
        return base, None
    top = sorted(issues, key=lambda i: SEVERITY_RANK[i["severity"]])[:60]
    listing = "\n".join(f'{i["id"]} | {i["severity"]} | {i["category"]} | {i["file_path"]} | {i["title"]}' for i in top)
    data = llm.complete_json(ROADMAP_SYSTEM, f"Issues:\n{listing}", max_tokens=2000)
    if not data or not isinstance(data.get("roadmap"), list):
        return base, None
    valid_ids = {i["id"] for i in issues}
    road = []
    for n, it in enumerate(data["roadmap"][:8], start=1):
        if not isinstance(it, dict) or not it.get("title"):
            continue
        effort = it.get("effort") if it.get("effort") in ("Low", "Medium", "High") else "Medium"
        ids = [x for x in it.get("issue_ids", []) if isinstance(x, int) and x in valid_ids][:15]
        road.append({"priority": n, "title": str(it["title"])[:200], "category": str(it.get("category", ""))[:30],
                     "effort": effort, "issue_ids": ids, "why": str(it.get("why", ""))[:300]})
    summary = str(data.get("summary", ""))[:800] or None
    return (road or base), summary
