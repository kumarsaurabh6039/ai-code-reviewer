import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..models import Analysis, Repository, User
from ..schemas.analysis import ScoreSet
from ..schemas.repository import GithubRepoCreate, RepositoryOut, UploadResult
from ..services.analysis_service import repo_dir, run_analysis
from ..services.github_service import GithubError, parse_github_url, validate_branch
from ..utils.file_utils import UnsafeArchiveError, remove_tree, safe_extract_zip
from .analysis import analysis_scores, issue_counts
from .deps import get_current_user, get_owned_repo

router = APIRouter(prefix="/repositories", tags=["repositories"])


def to_out(repo: Repository) -> RepositoryOut:
    a = repo.analyses[0] if repo.analyses else None
    done = next((x for x in repo.analyses if x.status == "completed"), None)
    return RepositoryOut(
        id=repo.id, name=repo.name, source=repo.source, github_url=repo.github_url, branch=repo.branch,
        language=repo.language, created_at=repo.created_at,
        latest_analysis_id=a.id if a else None, latest_status=a.status if a else None,
        scores=analysis_scores(done) if done else ScoreSet(),
        issue_counts=issue_counts(done) if done else {})


def _new_analysis(db: Session, repo: Repository, bg: BackgroundTasks) -> Analysis:
    analysis = Analysis(repository_id=repo.id, status="pending", stage="Queued", commit_sha=repo.commit_sha)
    db.add(analysis)
    db.commit()
    bg.add_task(run_analysis, analysis.id)
    return analysis


@router.get("", response_model=list[RepositoryOut])
def list_repositories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repos = db.query(Repository).filter(Repository.user_id == user.id).order_by(Repository.id.desc()).all()
    return [to_out(r) for r in repos]


@router.get("/{repo_id}", response_model=RepositoryOut)
def get_repository(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return to_out(get_owned_repo(db, repo_id, user))


@router.post("/zip", response_model=UploadResult, status_code=202)
def upload_zip(bg: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Please upload a .zip file")
    uploads = Path(settings.workdir).resolve() / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    tmp = uploads / f"{uuid.uuid4().hex}.zip"
    limit = settings.max_zip_mb * 1024 * 1024
    size, sha = 0, hashlib.sha256()
    try:
        with open(tmp, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"ZIP is larger than {settings.max_zip_mb} MB")
                sha.update(chunk)
                out.write(chunk)

        name = Path(file.filename).stem[:200] or "uploaded-project"
        repo = Repository(user_id=user.id, name=name, source="zip", commit_sha="zip:" + sha.hexdigest()[:12])
        db.add(repo)
        db.flush()
        dest = repo_dir(repo.id) / "src"
        try:
            root = safe_extract_zip(tmp, dest)
        except UnsafeArchiveError as e:
            db.rollback()
            remove_tree(repo_dir(repo.id))
            raise HTTPException(400, str(e))
        repo.local_path = str(root)
        db.commit()
    finally:
        tmp.unlink(missing_ok=True)
    analysis = _new_analysis(db, repo, bg)
    return UploadResult(repository_id=repo.id, analysis_id=analysis.id)


@router.post("/github", response_model=UploadResult, status_code=202)
def add_github(body: GithubRepoCreate, bg: BackgroundTasks, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    try:
        owner, name = parse_github_url(body.url)
        branch = validate_branch(body.branch)
    except GithubError as e:
        raise HTTPException(400, str(e))
    repo = Repository(user_id=user.id, name=f"{owner}/{name}", source="github",
                      github_url=f"https://github.com/{owner}/{name}", branch=branch)
    db.add(repo)
    db.commit()
    analysis = _new_analysis(db, repo, bg)
    return UploadResult(repository_id=repo.id, analysis_id=analysis.id)


@router.post("/{repo_id}/analyze", response_model=UploadResult, status_code=202)
def reanalyze(repo_id: int, bg: BackgroundTasks, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    if repo.analyses and repo.analyses[0].status in ("pending", "running"):
        raise HTTPException(409, "An analysis is already running")
    analysis = _new_analysis(db, repo, bg)
    return UploadResult(repository_id=repo.id, analysis_id=analysis.id)


@router.get("/{repo_id}/analyses")
def list_analyses(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    return [{"id": a.id, "status": a.status, "overall_score": a.overall_score, "created_at": a.created_at,
             "commit_sha": a.commit_sha} for a in repo.analyses]


@router.delete("/{repo_id}", status_code=204)
def delete_repository(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    remove_tree(repo_dir(repo.id))
    db.delete(repo)
    db.commit()
