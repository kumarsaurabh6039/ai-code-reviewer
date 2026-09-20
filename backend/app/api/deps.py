import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import decode_token
from ..models import Analysis, Issue, Repository, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if not creds:
        raise unauthorized
    try:
        payload = decode_token(creds.credentials)  # verifies signature AND expiry
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError):
        raise unauthorized
    if not user:
        raise unauthorized
    return user


def get_owned_repo(db: Session, repo_id: int, user: User) -> Repository:
    repo = db.get(Repository, repo_id)
    if not repo or repo.user_id != user.id:
        raise HTTPException(404, "Repository not found")
    return repo


def get_owned_analysis(db: Session, analysis_id: int, user: User) -> Analysis:
    a = db.get(Analysis, analysis_id)
    if not a or a.repository.user_id != user.id:
        raise HTTPException(404, "Analysis not found")
    return a


def get_owned_issue(db: Session, issue_id: int, user: User) -> Issue:
    i = db.get(Issue, issue_id)
    if not i or i.analysis.repository.user_id != user.id:
        raise HTTPException(404, "Issue not found")
    return i
