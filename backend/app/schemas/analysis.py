from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScoreSet(BaseModel):
    overall: int | None = None
    code_quality: int | None = None
    security: int | None = None
    performance: int | None = None
    architecture: int | None = None
    testing: int | None = None
    documentation: int | None = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    repository_id: int
    repository_name: str = ""
    status: str
    stage: str | None
    error: str | None
    commit_sha: str | None
    used_ai: bool
    scores: ScoreSet
    metrics: dict | None
    languages: dict | None
    summary: str | None
    roadmap: list | None
    issue_counts: dict
    created_at: datetime
    finished_at: datetime | None
