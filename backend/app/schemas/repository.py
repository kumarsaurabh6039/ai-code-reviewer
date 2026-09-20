from datetime import datetime

from pydantic import BaseModel, Field

from .analysis import ScoreSet


class GithubRepoCreate(BaseModel):
    url: str = Field(max_length=300)
    branch: str | None = Field(default=None, max_length=100)


class RepositoryOut(BaseModel):
    id: int
    name: str
    source: str
    github_url: str | None
    branch: str | None
    language: str | None
    created_at: datetime
    latest_analysis_id: int | None = None
    latest_status: str | None = None
    scores: ScoreSet = ScoreSet()
    issue_counts: dict = {}


class UploadResult(BaseModel):
    repository_id: int
    analysis_id: int


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ExplainCodeRequest(BaseModel):
    file_path: str = Field(max_length=600)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
