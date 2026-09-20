from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..ai.llm import get_llm
from ..core.database import get_db
from ..models import User
from ..schemas.issue import CodeView, ExplainOut, IssueOut, IssueStatusUpdate
from ..services.mentor_service import explain_issue
from .deps import get_current_user, get_owned_issue

router = APIRouter(prefix="/issues", tags=["issues"])


def read_lines(root: str | None, rel: str) -> list[str] | None:
    """Read a file from inside the repo root only (path traversal safe)."""
    if not root:
        return None
    base = Path(root).resolve()
    target = (base / rel).resolve()
    if base not in target.parents or not target.is_file():
        return None
    return target.read_text(encoding="utf-8", errors="replace").splitlines()


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(issue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_owned_issue(db, issue_id, user)


@router.patch("/{issue_id}", response_model=IssueOut)
def update_status(issue_id: int, body: IssueStatusUpdate, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    issue = get_owned_issue(db, issue_id, user)
    issue.status = body.status
    db.commit()
    return issue


@router.get("/{issue_id}/code", response_model=CodeView)
def view_code(issue_id: int, context: int = Query(default=12, ge=0, le=60), db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    issue = get_owned_issue(db, issue_id, user)
    lines = read_lines(issue.analysis.repository.local_path, issue.file_path)
    if lines is None:
        return CodeView(file_path=issue.file_path, start_line=1, highlight_start=issue.line_number,
                        highlight_end=issue.line_number, lines=["(file not available - it may be a project-level issue)"])
    end_hl = issue.end_line or issue.line_number
    start = max(1, issue.line_number - context)
    stop = min(len(lines), end_hl + context)
    return CodeView(file_path=issue.file_path, start_line=start, highlight_start=issue.line_number,
                    highlight_end=end_hl, lines=lines[start - 1:stop])


@router.post("/{issue_id}/explain", response_model=ExplainOut)
def explain(issue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    issue = get_owned_issue(db, issue_id, user)
    llm = get_llm()
    lines = read_lines(issue.analysis.repository.local_path, issue.file_path) or []
    s = max(0, issue.line_number - 15)
    code = "\n".join(f"{n}: {t}" for n, t in enumerate(lines[s:issue.line_number + 15], start=s + 1))
    result = explain_issue(llm, issue, code)
    return ExplainOut(**result, ai=llm.available)
