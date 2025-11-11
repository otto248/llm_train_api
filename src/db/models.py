"""Database table definitions for the training service."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text

from .base import metadata

projects_table = Table(
    "projects",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("description", Text, nullable=True),
    Column("owner", String, nullable=False),
    Column("tags", Text, nullable=False, default="[]"),
    Column("dataset_name", String, nullable=False),
    Column("training_yaml_name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("runs_started", Integer, nullable=False, default=0),
)

runs_table = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, ForeignKey("projects.id"), nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("started_at", DateTime, nullable=True),
    Column("completed_at", DateTime, nullable=True),
    Column("progress", Float, nullable=False, default=0.0),
    Column("metrics", Text, nullable=False, default="{}"),
    Column("start_command", Text, nullable=False),
    Column("resume_source_artifact_id", String, nullable=True),
)

logs_table = Table(
    "logs",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False, index=True),
    Column("timestamp", DateTime, nullable=False),
    Column("level", String, nullable=False),
    Column("message", Text, nullable=False),
)

artifacts_table = Table(
    "artifacts",
    metadata,
    Column("id", String, primary_key=True),
    Column("run_id", String, ForeignKey("runs.id"), nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("path", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("tags", Text, nullable=False, default="[]"),
)

operation_logs_table = Table(
    "operation_logs",
    metadata,
    Column("id", String, primary_key=True),
    Column("action", String, nullable=False),
    Column("target_type", String, nullable=False),
    Column("target_id", String, nullable=True),
    Column("status", String, nullable=False),
    Column("detail", Text, nullable=True),
    Column("extra", Text, nullable=False, default="{}"),
    Column("created_at", DateTime, nullable=False),
)

__all__ = [
    "projects_table",
    "runs_table",
    "logs_table",
    "artifacts_table",
    "operation_logs_table",
]
