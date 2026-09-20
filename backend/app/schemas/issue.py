from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    analysis_id: int
    file_path: str
    line_number: int
    end_line: int | None
    severity: str
    category: str
    title: str
    description: str
    suggestion: str
    fix_before: str | None
    fix_after: str | None
    explanation: str | None
    rule_id: str | None
    source: str
    confidence: float
    status: str
    created_at: datetime


class IssueStatusUpdate(BaseModel):
    status: Literal["open", "resolved", "ignored"]


class ExplainOut(BaseModel):
    explanation: str
    why_it_matters: str = ""
    before: str = ""
    after: str = ""
    ai: bool = False


class CodeView(BaseModel):
    file_path: str
    start_line: int
    highlight_start: int
    highlight_end: int
    lines: list[str]
