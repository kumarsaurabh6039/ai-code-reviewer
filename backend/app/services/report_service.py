import json

from ..models import Analysis, Issue, Repository

SEV_ICON = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}


def build_report_dict(repo: Repository, analysis: Analysis, issues: list[Issue]) -> dict:
    counts = {s: sum(1 for i in issues if i.severity == s) for s in ("critical", "high", "medium", "low")}
    return {
        "disclaimer": "Scores are an automated, heuristic assessment - not an industry certification.",
        "repository": {"name": repo.name, "source": repo.source, "url": repo.github_url, "language": repo.language},
        "analysis": {"id": analysis.id, "commit": analysis.commit_sha, "status": analysis.status,
                     "used_ai": analysis.used_ai, "finished_at": str(analysis.finished_at)},
        "scores": {"overall": analysis.overall_score, "code_quality": analysis.code_quality_score,
                   "security": analysis.security_score, "performance": analysis.performance_score,
                   "architecture": analysis.architecture_score, "testing": analysis.testing_score,
                   "documentation": analysis.documentation_score},
        "metrics": analysis.metrics, "languages": analysis.languages, "issue_counts": counts,
        "summary": analysis.summary, "roadmap": analysis.roadmap,
        "issues": [{"id": i.id, "severity": i.severity, "category": i.category, "title": i.title,
                    "file": i.file_path, "line": i.line_number, "description": i.description,
                    "suggestion": i.suggestion, "source": i.source, "status": i.status} for i in issues],
    }


def build_markdown(repo: Repository, analysis: Analysis, issues: list[Issue]) -> str:
    d = build_report_dict(repo, analysis, issues)
    s, m, c = d["scores"], d["metrics"] or {}, d["issue_counts"]
    out = [f"# Code Review Report - {repo.name}", "",
           f"> {d['disclaimer']}", "",
           f"- Analysis #{analysis.id}  |  Commit/version: `{analysis.commit_sha or 'n/a'}`  |  AI review: {'yes' if analysis.used_ai else 'no (static analysis only)'}",
           "", "## Health score", "",
           "| Area | Score |", "|---|---|",
           f"| **Overall** | **{s['overall']}/100** |", f"| Code quality | {s['code_quality']} |",
           f"| Security | {s['security']} |", f"| Performance | {s['performance']} |",
           f"| Architecture | {s['architecture']} |", f"| Testing | {s['testing']} |",
           f"| Documentation | {s['documentation']} |", "",
           "## Project overview", ""]
    if analysis.summary:
        out += [analysis.summary, ""]
    out += ["| Metric | Value |", "|---|---|"]
    for k in ("files", "lines", "functions", "classes", "test_files"):
        out.append(f"| {k.replace('_', ' ').title()} | {m.get(k, 0)} |")
    out += ["", "### Languages", ""]
    for lang, pct in (analysis.languages or {}).items():
        out.append(f"- {lang}: {pct}%")
    out += ["", f"## Issues ({len(issues)})", "",
            f"🔴 Critical {c['critical']}  |  🟠 High {c['high']}  |  🟡 Medium {c['medium']}  |  🔵 Low {c['low']}", ""]
    for i in issues:
        out += [f"### {SEV_ICON[i.severity]} [{i.severity.upper()}] {i.title}",
                f"`{i.file_path}:{i.line_number}` - {i.category}", "", i.description, "",
                f"**Suggested fix:** {i.suggestion}", ""]
    out += ["## Improvement roadmap", ""]
    for r in analysis.roadmap or []:
        out.append(f"**Priority {r['priority']} - {r['title']}**  \n{r.get('category', '')} | Effort: {r['effort']}  \n{r.get('why', '')}\n")
    return "\n".join(out)


def build_json(repo: Repository, analysis: Analysis, issues: list[Issue]) -> str:
    return json.dumps(build_report_dict(repo, analysis, issues), indent=2, default=str)
