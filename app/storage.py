from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.engine import Connection, Engine, Row

from .models import (
    Artifact,
    ArtifactListResponse,
    ArtifactTagRequest,
    LogEntry,
    LogListResponse,
    LogQueryParams,
    Project,
    ProjectCreate,
    ProjectDetail,
    ProjectStatus,
    Run,
    RunDetail,
    RunStatus,
)


_DEFAULT_DB_URL = os.getenv("TRAINING_DB_URL", "sqlite:///./training.db")


metadata = MetaData()


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


def _serialize_list(values: Sequence[str]) -> str:
    return json.dumps(list(values))


def _deserialize_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return json.loads(raw)


def _serialize_metrics(metrics: Dict[str, float]) -> str:
    return json.dumps(metrics)


def _deserialize_metrics(raw: Optional[str]) -> Dict[str, float]:
    if not raw:
        return {}
    return json.loads(raw)


class DatabaseStorage:
    """基于关系型数据库的持久化存储实现。"""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self._database_url = database_url or _DEFAULT_DB_URL
        self._engine: Engine = create_engine(self._database_url, future=True)
        metadata.create_all(self._engine)

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------
    def create_project(self, payload: ProjectCreate) -> ProjectDetail:
        project_id = str(uuid4())
        timestamp = datetime.utcnow()
        with self._engine.begin() as conn:
            conn.execute(
                projects_table.insert().values(
                    id=project_id,
                    name=payload.name,
                    description=payload.description,
                    owner=payload.owner,
                    tags=_serialize_list(payload.tags),
                    dataset_name=payload.dataset_name,
                    training_yaml_name=payload.training_yaml_name,
                    status=ProjectStatus.ACTIVE.value,
                    created_at=timestamp,
                    updated_at=timestamp,
                    runs_started=0,
                )
            )
        project = self.get_project(project_id)
        if project is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Project creation failed")
        return project

    def list_projects(self) -> Iterable[Project]:
        with self._engine.connect() as conn:
            result = conn.execute(select(projects_table).order_by(projects_table.c.created_at))
            return [self._row_to_project(row) for row in result]

    def get_project(self, project_id: str) -> Optional[ProjectDetail]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(projects_table).where(projects_table.c.id == project_id)
            ).one_or_none()
            if row is None:
                return None
            return self._row_to_project_detail(conn, row)

    def get_project_by_name(self, project_name: str) -> Optional[ProjectDetail]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(projects_table).where(projects_table.c.name == project_name)
            ).one_or_none()
            if row is None:
                return None
            return self._row_to_project_detail(conn, row)

    # ------------------------------------------------------------------
    # Run operations
    # ------------------------------------------------------------------
    def create_run(
        self,
        project_id: str,
        start_command: str,
        resume_source_artifact_id: Optional[str] = None,
    ) -> RunDetail:
        run_id = str(uuid4())
        timestamp = datetime.utcnow()
        with self._engine.begin() as conn:
            conn.execute(
                runs_table.insert().values(
                    id=run_id,
                    project_id=project_id,
                    status=RunStatus.PENDING.value,
                    created_at=timestamp,
                    updated_at=timestamp,
                    started_at=None,
                    completed_at=None,
                    progress=0.0,
                    metrics=_serialize_metrics({}),
                    start_command=start_command,
                    resume_source_artifact_id=resume_source_artifact_id,
                )
            )
            self._insert_initial_artifacts(conn, project_id, run_id, timestamp)
            self._insert_initial_logs(conn, run_id, timestamp)
            project_row = conn.execute(
                select(projects_table.c.runs_started).where(projects_table.c.id == project_id)
            ).one()
            conn.execute(
                projects_table.update()
                .where(projects_table.c.id == project_id)
                .values(
                    runs_started=project_row.runs_started + 1,
                    updated_at=datetime.utcnow(),
                )
            )
        run = self.get_run(run_id)
        if run is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Run creation failed")
        return run

    def get_run(self, run_id: str) -> Optional[RunDetail]:
        with self._engine.connect() as conn:
            row = conn.execute(select(runs_table).where(runs_table.c.id == run_id)).one_or_none()
            if row is None:
                return None
            return self._row_to_run_detail(conn, row)

    def iter_project_runs(self, project_id: str) -> Iterable[RunDetail]:
        project = self.get_project(project_id)
        if project is None:
            return []
        return project.runs

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        progress: Optional[float] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> RunDetail:
        now = datetime.utcnow()
        with self._engine.begin() as conn:
            row = conn.execute(select(runs_table).where(runs_table.c.id == run_id)).one_or_none()
            if row is None:
                raise KeyError(f"Run {run_id} not found")
            updates: Dict[str, object] = {
                "status": status.value,
                "updated_at": now,
            }
            if status == RunStatus.RUNNING and row.started_at is None:
                updates["started_at"] = now
            if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED}:
                updates["completed_at"] = now
            if progress is not None:
                updates["progress"] = progress
            if metrics is not None:
                existing_metrics = _deserialize_metrics(row.metrics)
                existing_metrics.update(metrics)
                updates["metrics"] = _serialize_metrics(existing_metrics)
            conn.execute(
                runs_table.update().where(runs_table.c.id == run_id).values(**updates)
            )
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(f"Run {run_id} not found")
        return run

    def append_run_logs(self, run_id: str, entries: Sequence[LogEntry]) -> RunDetail:
        if not entries:
            run = self.get_run(run_id)
            if run is None:
                raise KeyError(f"Run {run_id} not found")
            return run
        with self._engine.begin() as conn:
            for entry in entries:
                conn.execute(
                    logs_table.insert().values(
                        id=str(uuid4()),
                        run_id=run_id,
                        timestamp=entry.timestamp,
                        level=entry.level,
                        message=entry.message,
                    )
                )
            conn.execute(
                runs_table.update()
                .where(runs_table.c.id == run_id)
                .values(updated_at=datetime.utcnow())
            )
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(f"Run {run_id} not found")
        return run

    # ------------------------------------------------------------------
    # Log operations
    # ------------------------------------------------------------------
    def get_logs(self, run_id: str, params: LogQueryParams) -> LogListResponse:
        with self._engine.connect() as conn:
            stmt = select(logs_table).where(logs_table.c.run_id == run_id).order_by(
                logs_table.c.timestamp
            )
            rows = conn.execute(stmt).all()
            filtered_rows = self._filter_logs(rows, params)
            start_index = (params.page - 1) * params.page_size
            end_index = start_index + params.page_size
            page_rows = filtered_rows[start_index:end_index]
            entries = [self._row_to_log(row) for row in page_rows]
            return LogListResponse(
                run_id=run_id,
                total=len(filtered_rows),
                page=params.page,
                page_size=params.page_size,
                entries=entries,
            )

    def _filter_logs(self, rows: Sequence[Row], params: LogQueryParams) -> List[Row]:
        filtered = list(rows)
        if params.start_time is not None:
            filtered = [row for row in filtered if row.timestamp >= params.start_time]
        if params.end_time is not None:
            filtered = [row for row in filtered if row.timestamp <= params.end_time]
        return filtered

    # ------------------------------------------------------------------
    # Artifact operations
    # ------------------------------------------------------------------
    def list_artifacts(self, run_id: str) -> ArtifactListResponse:
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(artifacts_table)
                .where(artifacts_table.c.run_id == run_id)
                .order_by(artifacts_table.c.created_at)
            ).all()
            artifacts = [self._row_to_artifact(row) for row in rows]
            return ArtifactListResponse(run_id=run_id, artifacts=artifacts)

    def tag_artifact(
        self, run_id: str, artifact_id: str, payload: ArtifactTagRequest
    ) -> Artifact:
        now = datetime.utcnow()
        with self._engine.begin() as conn:
            row = conn.execute(
                select(artifacts_table)
                .where(
                    artifacts_table.c.id == artifact_id,
                    artifacts_table.c.run_id == run_id,
                )
            ).one_or_none()
            if row is None:
                raise KeyError(f"Artifact {artifact_id} not found")
            tags = _deserialize_list(row.tags)
            if payload.tag not in tags:
                tags.append(payload.tag)
                conn.execute(
                    artifacts_table.update()
                    .where(artifacts_table.c.id == artifact_id)
                    .values(tags=_serialize_list(tags))
                )
                conn.execute(
                    runs_table.update()
                    .where(runs_table.c.id == run_id)
                    .values(updated_at=now)
                )
        artifact = self.get_artifact(artifact_id)
        if artifact is None:
            raise KeyError(f"Artifact {artifact_id} not found")
        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(artifacts_table).where(artifacts_table.c.id == artifact_id)
            ).one_or_none()
            if row is None:
                return None
            return self._row_to_artifact(row)

    # ------------------------------------------------------------------
    # Helper builders
    # ------------------------------------------------------------------
    def _row_to_project(self, row: Row) -> Project:
        return Project(
            id=row.id,
            name=row.name,
            description=row.description,
            owner=row.owner,
            tags=_deserialize_list(row.tags),
            dataset_name=row.dataset_name,
            training_yaml_name=row.training_yaml_name,
            status=ProjectStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
            runs_started=row.runs_started,
        )

    def _row_to_project_detail(self, conn: Connection, row: Row) -> ProjectDetail:
        runs = self._load_runs_for_project(conn, row.id)
        return ProjectDetail(
            **self._row_to_project(row).model_dump(),
            runs=runs,
        )

    def _row_to_run_detail(self, conn: Connection, row: Row) -> RunDetail:
        artifacts = self._load_artifacts_for_run(conn, row.id)
        logs = self._load_logs_for_run(conn, row.id)
        return RunDetail(
            id=row.id,
            project_id=row.project_id,
            status=RunStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            progress=row.progress,
            metrics=_deserialize_metrics(row.metrics),
            start_command=row.start_command,
            artifacts=artifacts,
            logs=logs,
            resume_source_artifact_id=row.resume_source_artifact_id,
        )

    def _load_runs_for_project(self, conn: Connection, project_id: str) -> List[RunDetail]:
        rows = conn.execute(
            select(runs_table)
            .where(runs_table.c.project_id == project_id)
            .order_by(runs_table.c.created_at)
        ).all()
        return [self._row_to_run_detail(conn, row) for row in rows]

    def _load_logs_for_run(self, conn: Connection, run_id: str) -> List[LogEntry]:
        rows = conn.execute(
            select(logs_table)
            .where(logs_table.c.run_id == run_id)
            .order_by(logs_table.c.timestamp)
        ).all()
        return [self._row_to_log(row) for row in rows]

    def _load_artifacts_for_run(self, conn: Connection, run_id: str) -> List[Artifact]:
        rows = conn.execute(
            select(artifacts_table)
            .where(artifacts_table.c.run_id == run_id)
            .order_by(artifacts_table.c.created_at)
        ).all()
        return [self._row_to_artifact(row) for row in rows]

    def _row_to_log(self, row: Row) -> LogEntry:
        return LogEntry(timestamp=row.timestamp, level=row.level, message=row.message)

    def _row_to_artifact(self, row: Row) -> Artifact:
        return Artifact(
            id=row.id,
            name=row.name,
            type=row.type,
            path=row.path,
            created_at=row.created_at,
            tags=_deserialize_list(row.tags),
        )

    def _insert_initial_logs(self, conn: Connection, run_id: str, timestamp: datetime) -> None:
        templates = [
            ("INFO", "Run created"),
            ("INFO", "Initializing resources"),
            ("INFO", "Loading dataset"),
            ("INFO", "Starting training loop"),
        ]
        for level, message in templates:
            conn.execute(
                logs_table.insert().values(
                    id=str(uuid4()),
                    run_id=run_id,
                    timestamp=timestamp,
                    level=level,
                    message=message,
                )
            )

    def _insert_initial_artifacts(
        self, conn: Connection, project_id: str, run_id: str, timestamp: datetime
    ) -> None:
        templates = [
            ("checkpoint", "checkpoint_step_0.pt"),
            ("tensorboard", "events.out.tfevents"),
            ("config", "training_config.yaml"),
        ]
        for artifact_type, name in templates:
            conn.execute(
                artifacts_table.insert().values(
                    id=str(uuid4()),
                    run_id=run_id,
                    name=name,
                    type=artifact_type,
                    path=f"s3://artifacts/{project_id}/{run_id}/{name}",
                    created_at=timestamp,
                    tags=_serialize_list([]),
                )
            )


storage = DatabaseStorage()

