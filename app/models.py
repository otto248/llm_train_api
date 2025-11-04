from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[str] = mapped_column(String(50))
    goal: Mapped[Optional[str]] = mapped_column(Text())
    version: Mapped[Optional[str]] = mapped_column(String(50))
    base_model: Mapped[Optional[str]] = mapped_column(String(100))
    owner: Mapped[Optional[str]] = mapped_column(String(100))
    param_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    runs: Mapped[List["Run"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")
    events: Mapped[List["ExperimentEvent"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", order_by="ExperimentEvent.created_at"
    )
    idempotency_records: Mapped[List["IdempotencyKey"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    checkpoint_tags: Mapped[List["CheckpointTag"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentEvent(Base):
    __tablename__ = "experiment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    event: Mapped[str] = mapped_column(String(50))
    detail: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="events")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(50), default="CREATED")
    model_name: Mapped[Optional[str]] = mapped_column(String(255))
    dataset: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    hyperparams: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    resources: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text())
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    latest_metrics: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    checkpoint_path: Mapped[Optional[str]] = mapped_column(Text())
    parent_run_id: Mapped[Optional[str]] = mapped_column(String(64))
    from_checkpoint: Mapped[Optional[str]] = mapped_column(Text())

    experiment: Mapped[Experiment] = relationship(back_populates="runs")
    checkpoint_tags: Mapped[List["CheckpointTag"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CheckpointTag(Base):
    __tablename__ = "checkpoint_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    ckpt_path: Mapped[str] = mapped_column(Text())
    tag_type: Mapped[str] = mapped_column(String(50))
    is_candidate_base: Mapped[bool] = mapped_column(Boolean, default=False)
    release_tag: Mapped[Optional[str]] = mapped_column(String(100))
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="checkpoint_tags")
    run: Mapped[Run] = relationship(back_populates="checkpoint_tags")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(128))
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="idempotency_records")
