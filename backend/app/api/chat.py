from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..ai.llm import get_llm
from ..core.database import get_db
from ..models import ChatMessage, CodeChunk, User
from ..schemas.repository import ChatRequest, ExplainCodeRequest
from ..services.mentor_service import ask_mentor, explain_code
from .deps import get_current_user, get_owned_repo
from .issues import read_lines

router = APIRouter(prefix="/mentor", tags=["mentor"])


@router.get("/{repo_id}/messages")
def messages(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    rows = db.query(ChatMessage).filter(ChatMessage.repository_id == repo.id).order_by(ChatMessage.id).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "sources": m.sources or []} for m in rows]


@router.post("/{repo_id}/chat")
def chat(repo_id: int, body: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    question = body.message.strip()
    answer, sources = ask_mentor(db, get_llm(), repo, question)
    db.add(ChatMessage(repository_id=repo.id, role="user", content=question))
    msg = ChatMessage(repository_id=repo.id, role="assistant", content=answer, sources=sources)
    db.add(msg)
    db.commit()
    return {"id": msg.id, "role": "assistant", "content": answer, "sources": sources}


@router.delete("/{repo_id}/messages", status_code=204)
def clear(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    db.query(ChatMessage).filter(ChatMessage.repository_id == repo.id).delete()
    db.commit()


@router.get("/{repo_id}/files")
def files(repo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    rows = db.query(CodeChunk.file_path).filter(CodeChunk.repository_id == repo.id).distinct().all()
    return sorted(r[0] for r in rows)


@router.post("/{repo_id}/explain-code")
def explain_selection(repo_id: int, body: ExplainCodeRequest, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    repo = get_owned_repo(db, repo_id, user)
    lines = read_lines(repo.local_path, body.file_path)
    if lines is None:
        raise HTTPException(404, "File not found in this repository")
    end = min(max(body.end_line, body.start_line), body.start_line + 200, len(lines))
    code = "\n".join(f"{n}: {t}" for n, t in enumerate(lines[body.start_line - 1:end], start=body.start_line))
    if not code.strip():
        raise HTTPException(400, "Selected line range is empty")
    return {"explanation": explain_code(get_llm(), body.file_path, code)}
