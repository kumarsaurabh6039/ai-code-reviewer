"""Orchestrates the whole pipeline. Runs in a background thread; progress is stored in analyses.stage."""
import json
import logging
import subprocess
import sys
from collections import Counter
from pathlib import Path

from ..ai import retriever
from ..ai.llm import get_llm
from ..analyzers.architecture_analyzer import analyze_architecture
from ..analyzers.base import SEVERITY_RANK, Finding
from ..analyzers.duplicate_analyzer import analyze_duplicates
from ..analyzers.javascript_analyzer import analyze_javascript
from ..analyzers.project_analyzer import analyze_project
from ..analyzers.python_analyzer import analyze_python
from ..analyzers.security_analyzer import analyze_security
from ..analyzers.testing_analyzer import analyze_testing
from ..core.config import settings
from ..core.database import SessionLocal, utcnow
from ..models import Analysis, CodeChunk, Issue, Repository
from ..utils.code_chunker import chunk_file
from ..utils.file_utils import ScanResult, scan_repository
from ..utils.language_detector import CODE_LANGS
from .github_service import clone_repo
from .review_service import ai_review, build_roadmap
from .scoring_service import compute_scores

log = logging.getLogger("analysis")
MAX_PER_RULE = 10
MAX_ISSUES = 250
BANDIT_SKIP = {"B101", "B404", "B603", "B607", "B110", "B311"}


def repo_dir(repo_id: int) -> Path:
    return Path(settings.workdir).resolve() / "repos" / str(repo_id)


def _run_bandit(root: Path) -> list[Finding]:
    """Optional: Bandit only parses code (AST), it does not execute it."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", str(root), "-f", "json", "-q",
             "-x", "node_modules,venv,.venv,tests,test,__pycache__"],
            capture_output=True, text=True, timeout=120)
        data = json.loads(proc.stdout or "{}")
    except Exception as e:
        log.info("bandit skipped: %s", e)
        return []
    sev_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    out = []
    for r in data.get("results", []):
        if r.get("test_id") in BANDIT_SKIP:
            continue
        try:
            rel = Path(r["filename"]).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        out.append(Finding(rel, int(r.get("line_number", 1)), sev_map.get(r.get("issue_severity", "LOW"), "low"),
                           "security", f"{r.get('test_name', 'bandit').replace('_', ' ').capitalize()} ({r.get('test_id')})",
                           r.get("issue_text", ""), (r.get("more_info") and f"See {r['more_info']}") or "",
                           f"BANDIT-{r.get('test_id')}", confidence=0.7))
    return out


def run_static(scan: ScanResult, use_bandit: bool = True) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    funcs = classes = pub = doc = 0
    for fi in scan.files:
        if fi.language == "Python":
            f, st = analyze_python(fi)
            findings += f
            funcs += st["functions"]; classes += st["classes"]
            pub += st["public_functions"]; doc += st["documented"]
        elif fi.language in {"JavaScript", "TypeScript"}:
            f, st = analyze_javascript(fi)
            findings += f
            funcs += st["functions"]; classes += st["classes"]
        findings += analyze_security(fi)

    if use_bandit and any(f.language == "Python" for f in scan.files):
        static_sec = [f for f in findings if f.category == "security"]
        for b in _run_bandit(scan.root):
            if not any(s.file_path == b.file_path and abs(s.line - b.line) <= 1 for s in static_sec):
                findings.append(b)

    findings += analyze_duplicates(scan.files)
    findings += analyze_architecture(scan.files)
    tf, tstats = analyze_testing(scan.files)
    findings += tf
    root_names = {p.name for p in scan.root.iterdir()}
    pf, pstats = analyze_project(scan.files, root_names)
    findings += pf

    stats = {"functions": funcs, "classes": classes, **tstats, **pstats,
             "docstring_coverage": round(doc / pub, 2) if pub else None}
    return findings, stats


def cap_findings(findings: list[Finding]) -> list[Finding]:
    seen, per_rule, out = set(), Counter(), []
    for f in sorted(findings, key=lambda f: (SEVERITY_RANK[f.severity], f.file_path, f.line)):
        key = (f.file_path, f.line, f.rule_id or f.title)
        if key in seen:
            continue
        seen.add(key)
        if f.severity in ("low", "medium") or f.source == "static":
            per_rule[f.rule_id] += 1
            if per_rule[f.rule_id] > MAX_PER_RULE and f.severity != "critical":
                continue
        out.append(f)
    return out[:MAX_ISSUES]


def _set_stage(db, analysis: Analysis, stage: str, status: str | None = None) -> None:
    analysis.stage = stage
    if status:
        analysis.status = status
    db.commit()


def run_analysis(analysis_id: int) -> None:
    db = SessionLocal()
    analysis = db.get(Analysis, analysis_id)
    try:
        repo = db.get(Repository, analysis.repository_id)
        _set_stage(db, analysis, "Preparing repository", "running")

        if repo.source == "github":
            _set_stage(db, analysis, "Cloning GitHub repository")
            dest = repo_dir(repo.id) / "src"
            repo.commit_sha = clone_repo(repo.github_url, dest, repo.branch)
            repo.local_path = str(dest)
        if not repo.local_path or not Path(repo.local_path).exists():
            raise RuntimeError("Repository files are missing on the server. Please upload again.")
        analysis.commit_sha = repo.commit_sha
        root = Path(repo.local_path)

        _set_stage(db, analysis, "Scanning files")
        scan = scan_repository(root)
        if not scan.files:
            raise RuntimeError("No supported source files found (Python, JS/TS, HTML, CSS, JSON, SQL).")

        _set_stage(db, analysis, "Running static analysis")
        findings, stats = run_static(scan)

        _set_stage(db, analysis, "Creating code chunks")
        db.query(CodeChunk).filter(CodeChunk.repository_id == repo.id).delete()
        chunk_rows, n_chunks = [], 0
        for fi in scan.files:
            if fi.language in {"JSON", "Config"} and fi.size > 20_000:
                continue
            for c in chunk_file(fi.rel_path, fi.language, fi.content):
                if n_chunks >= 4000:
                    break
                n_chunks += 1
                chunk_rows.append(CodeChunk(repository_id=repo.id, file_path=c.file_path, start_line=c.start_line,
                                            end_line=c.end_line, language=c.language, content=c.content))
        db.add_all(chunk_rows)
        retriever.invalidate(repo.id)
        db.commit()

        llm = get_llm()
        if llm.available:
            _set_stage(db, analysis, "AI review of high-risk files")
            try:
                findings += ai_review(llm, scan.files, findings, lambda s: _set_stage(db, analysis, s))
                analysis.used_ai = True
            except Exception:
                log.exception("AI review failed; continuing with static results")

        _set_stage(db, analysis, "Saving issues")
        findings = cap_findings(findings)
        db.query(Issue).filter(Issue.analysis_id == analysis.id).delete()
        rows = [Issue(analysis_id=analysis.id, file_path=f.file_path, line_number=f.line, end_line=f.end_line,
                      severity=f.severity, category=f.category, title=f.title[:300], description=f.description,
                      suggestion=f.suggestion, fix_before=f.fix_before or None, fix_after=f.fix_after or None,
                      rule_id=f.rule_id, source=f.source, confidence=f.confidence) for f in findings]
        db.add_all(rows)
        db.flush()

        _set_stage(db, analysis, "Calculating scores")
        code_files = [f for f in scan.files if f.language in CODE_LANGS]
        loc = sum(f.loc for f in code_files)
        by_lang = Counter()
        for f in code_files:
            by_lang[f.language] += f.loc
        analysis.languages = {k: round(v * 100 / max(loc, 1), 1) for k, v in by_lang.most_common()}
        repo.language = by_lang.most_common(1)[0][0] if by_lang else None
        analysis.metrics = {
            "files": len(scan.files), "lines": loc, "functions": stats["functions"], "classes": stats["classes"],
            "test_files": stats["test_files"], "source_files": stats["source_files"],
            "untested_modules": stats["untested_modules"], "skipped_files": len(scan.skipped),
            "dependencies": stats["dependencies"], "docstring_coverage": stats["docstring_coverage"],
            "readme": stats["readme"],
        }
        s = compute_scores([{"severity": r.severity, "category": r.category, "confidence": r.confidence} for r in rows],
                           loc, stats["source_files"], stats["test_files"], stats["readme_lines"],
                           stats["docstring_coverage"])
        analysis.overall_score, analysis.code_quality_score = s["overall"], s["code_quality"]
        analysis.security_score, analysis.performance_score = s["security"], s["performance"]
        analysis.architecture_score, analysis.testing_score = s["architecture"], s["testing"]
        analysis.documentation_score = s["documentation"]

        _set_stage(db, analysis, "Building roadmap")
        issue_dicts = [{"id": r.id, "severity": r.severity, "category": r.category, "title": r.title,
                        "rule_id": r.rule_id, "description": r.description, "file_path": r.file_path} for r in rows]
        analysis.roadmap, ai_summary = build_roadmap(llm, issue_dicts)
        counts = Counter(r.severity for r in rows)
        analysis.summary = ai_summary or (
            f"Found {len(rows)} issues ({counts['critical']} critical, {counts['high']} high, "
            f"{counts['medium']} medium, {counts['low']} low) across {len(scan.files)} files. "
            + ("AI review was included." if analysis.used_ai else "Static analysis only (set ANTHROPIC_API_KEY to enable AI review)."))
        analysis.status, analysis.stage, analysis.finished_at = "completed", "Done", utcnow()
        db.commit()
    except Exception as e:
        log.exception("analysis %s failed", analysis_id)
        db.rollback()
        a = db.get(Analysis, analysis_id)
        a.status, a.stage, a.error = "failed", "Failed", str(e)[:500]
        db.commit()
    finally:
        db.close()
