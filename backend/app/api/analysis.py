from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..analyzers.base import SEVERITY_RANK
from ..core.database import get_db
from ..models import Analysis, Issue, Repository, User
from ..schemas.analysis import AnalysisOut, ScoreSet
from ..schemas.issue import IssueOut
from ..services.report_service import build_json, build_markdown
from .deps import get_current_user, get_owned_analysis

router = APIRouter(tags=["analysis"])


def analysis_scores(a: Analysis) -> ScoreSet:
    return ScoreSet(overall=a.overall_score, code_quality=a.code_quality_score, security=a.security_score,
                    performance=a.performance_score, architecture=a.architecture_score,
                    testing=a.testing_score, documentation=a.documentation_score)


def issue_counts(a: Analysis, only_open: bool = True) -> dict:
    c = Counter(i.severity for i in a.issues if not only_open or i.status == "open")
    return {s: c.get(s, 0) for s in ("critical", "high", "medium", "low")}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repos = db.query(Repository).filter(Repository.user_id == user.id).all()
    latest = []
    for r in repos:
        done = next((a for a in r.analyses if a.status == "completed"), None)
        if done:
            latest.append(done)
    totals = Counter()
    for a in latest:
        totals.update(issue_counts(a))
    scores = [a.overall_score for a in latest if a.overall_score is not None]
    recent = db.query(Analysis).join(Repository).filter(Repository.user_id == user.id) \
        .order_by(Analysis.id.desc()).limit(6).all()
    return {
        "repositories": len(repos),
        "average_score": round(sum(scores) / len(scores)) if scores else None,
        "open_issues": {s: totals.get(s, 0) for s in ("critical", "high", "medium", "low")},
        "recent": [{"id": a.id, "repository_id": a.repository_id, "repository_name": a.repository.name,
                    "status": a.status, "overall_score": a.overall_score, "created_at": a.created_at} for a in recent],
    }


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = get_owned_analysis(db, analysis_id, user)
    return AnalysisOut(
        id=a.id, repository_id=a.repository_id, repository_name=a.repository.name, status=a.status, stage=a.stage,
        error=a.error, commit_sha=a.commit_sha, used_ai=a.used_ai, scores=analysis_scores(a), metrics=a.metrics,
        languages=a.languages, summary=a.summary, roadmap=a.roadmap, issue_counts=issue_counts(a),
        created_at=a.created_at, finished_at=a.finished_at)


@router.get("/analyses/{analysis_id}/issues", response_model=list[IssueOut])
def list_issues(analysis_id: int, severity: str | None = None, category: str | None = None,
                status: str | None = Query(default=None), db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    a = get_owned_analysis(db, analysis_id, user)
    issues = a.issues
    if severity:
        issues = [i for i in issues if i.severity == severity]
    if category:
        issues = [i for i in issues if i.category == category]
    if status:
        issues = [i for i in issues if i.status == status]
    return sorted(issues, key=lambda i: (SEVERITY_RANK[i.severity], i.file_path, i.line_number))


@router.get("/analyses/{analysis_id}/report")
def report(analysis_id: int, format: str = "md", db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    a = get_owned_analysis(db, analysis_id, user)
    if a.status != "completed":
        raise HTTPException(409, "Analysis is not finished yet")
    issues = sorted(a.issues, key=lambda i: (SEVERITY_RANK[i.severity], i.file_path, i.line_number))
    if format == "json":
        return PlainTextResponse(build_json(a.repository, a, issues), media_type="application/json",
                                 headers={"Content-Disposition": f'attachment; filename="report-{a.id}.json"'})
    if format == "md":
        return PlainTextResponse(build_markdown(a.repository, a, issues), media_type="text/markdown",
                                 headers={"Content-Disposition": f'attachment; filename="report-{a.id}.md"'})
    raise HTTPException(400, "format must be 'md' or 'json'")
