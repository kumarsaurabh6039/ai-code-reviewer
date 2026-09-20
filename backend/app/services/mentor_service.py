from sqlalchemy.orm import Session

from ..ai import retriever
from ..ai.llm import LLMClient
from ..ai.prompts import EXPLAIN_CODE_SYSTEM, EXPLAIN_SYSTEM, MENTOR_SYSTEM
from ..analyzers.base import SEVERITY_RANK
from ..models import Analysis, ChatMessage, CodeChunk, Issue, Repository


def _issue_context(db: Session, repo: Repository, limit: int = 10) -> str:
    a = db.query(Analysis).filter(Analysis.repository_id == repo.id, Analysis.status == "completed") \
        .order_by(Analysis.id.desc()).first()
    if not a:
        return "(no analysis yet)"
    issues = sorted(a.issues, key=lambda i: SEVERITY_RANK[i.severity])[:limit]
    return "\n".join(f"- [{i.severity}] {i.file_path}:{i.line_number} {i.title}" for i in issues) or "(no issues)"


def ask_mentor(db: Session, llm: LLMClient, repo: Repository, question: str) -> tuple[str, list[dict]]:
    chunks = db.query(CodeChunk).filter(CodeChunk.repository_id == repo.id).all()
    if not chunks:
        return "This repository has no indexed code yet. Run an analysis first.", []
    top = retriever.get_index(repo.id, chunks).search(question, k=6)
    sources = [{"file": c.file_path, "start_line": c.start_line, "end_line": c.end_line} for c in top]

    if not llm.available:
        body = "\n\n".join(f"**{c.file_path}:{c.start_line}-{c.end_line}**\n```\n{c.content[:1200]}\n```" for c in top[:3])
        return ("AI is not configured (ANTHROPIC_API_KEY missing), so here are the most relevant code excerpts "
                "I found for your question:\n\n" + (body or "No relevant code found."), sources)

    history = db.query(ChatMessage).filter(ChatMessage.repository_id == repo.id) \
        .order_by(ChatMessage.id.desc()).limit(6).all()[::-1]
    context = "\n\n".join(f'<excerpt path="{c.file_path}" lines="{c.start_line}-{c.end_line}">\n'
                          f'{c.content.replace("</excerpt>", "</ excerpt>")}\n</excerpt>' for c in top)
    user = (f"Known issues in this project:\n{_issue_context(db, repo)}\n\nRelevant code:\n{context}\n\n"
            f"Question: {question}")
    messages = [{"role": m.role, "content": m.content} for m in history] + [{"role": "user", "content": user}]
    answer = llm.complete(MENTOR_SYSTEM, messages, max_tokens=1500)
    return (answer or "The AI service did not respond. Please try again.", sources)


def explain_issue(llm: LLMClient, issue: Issue, code: str) -> dict:
    fallback = {"explanation": issue.description, "why_it_matters": "", "before": issue.fix_before or "",
                "after": issue.fix_after or issue.suggestion}
    if not llm.available:
        return fallback
    user = (f"Issue: [{issue.severity}] {issue.title}\nFile: {issue.file_path} line {issue.line_number}\n"
            f"Detected problem: {issue.description}\n\n<code>\n{code.replace('</code>', '</ code>')}\n</code>")
    data = llm.complete_json(EXPLAIN_SYSTEM, user, max_tokens=900)
    if not data:
        return fallback
    return {k: str(data.get(k, fallback[k]))[:2000] for k in fallback}


def explain_code(llm: LLMClient, path: str, code: str) -> str:
    if not llm.available:
        return "AI is not configured. Set ANTHROPIC_API_KEY in backend/.env to use 'Explain this code'."
    user = f"File: {path}\n\n<code>\n{code.replace('</code>', '</ code>')}\n</code>"
    return llm.complete(EXPLAIN_CODE_SYSTEM, user, max_tokens=1200) or "The AI service did not respond."
