from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base, utcnow


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|completed|failed
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(80), nullable=True)
    used_ai: Mapped[bool] = mapped_column(default=False)

    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    architecture_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    testing_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    documentation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    languages: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    roadmap: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="analyses")
    issues = relationship("Issue", back_populates="analysis", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(600))
    line_number: Mapped[int] = mapped_column(Integer, default=1)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)  # critical|high|medium|low
    category: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text, default="")
    fix_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # cached AI explanation
    rule_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="static")  # static | ai
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|resolved|ignored
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    analysis = relationship("Analysis", back_populates="issues")
