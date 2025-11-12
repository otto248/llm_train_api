from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.utils import utcnow
from app.db.base import Base


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    dataset_name: Mapped[str] = mapped_column(String(512), nullable=False)
    training_yaml_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    runs_started: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    runs: Mapped[list["RunORM"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="RunORM.created_at"
    )


class RunORM(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress: Mapped[float] = mapped_column(Float(), nullable=False, default=0.0)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON(), nullable=False, default=dict)
    start_command: Mapped[str] = mapped_column(Text(), nullable=False)
    resume_source_artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    project: Mapped[ProjectORM] = relationship(back_populates="runs")
    artifacts: Mapped[list["RunArtifactORM"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunArtifactORM.created_at"
    )
    logs: Mapped[list["RunLogORM"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="RunLogORM.timestamp"
    )


class RunArtifactORM(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)

    run: Mapped["RunORM"] = relationship(back_populates="artifacts")


class RunLogORM(Base):
    __tablename__ = "run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text(), nullable=False)

    run: Mapped["RunORM"] = relationship(back_populates="logs")
