from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.projects import models
from app.api.v1.projects.schemas import ProjectCreate, RunStatus
from app.common.utils import utcnow


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # Project operations
    def create_project(self, payload: ProjectCreate) -> models.ProjectORM:
        project = models.ProjectORM(
            name=payload.name,
            description=payload.description,
            owner=payload.owner,
            tags=payload.tags,
            dataset_name=payload.dataset_name,
            training_yaml_name=payload.training_yaml_name,
            status="active",
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list_projects(self) -> Iterable[models.ProjectORM]:
        stmt = select(models.ProjectORM).order_by(models.ProjectORM.created_at)
        return self.db.scalars(stmt).all()

    def get_project_by_id(self, project_id: str) -> Optional[models.ProjectORM]:
        return self.db.get(models.ProjectORM, project_id)

    def get_project_by_name(self, name: str) -> Optional[models.ProjectORM]:
        stmt = select(models.ProjectORM).where(models.ProjectORM.name == name)
        return self.db.scalars(stmt).first()

    # Run operations
    def create_run(
        self,
        project: models.ProjectORM,
        start_command: str,
        resume_source_artifact_id: str | None = None,
    ) -> models.RunORM:
        run_id = str(uuid4())
        run = models.RunORM(
            id=run_id,
            project=project,
            start_command=start_command,
            resume_source_artifact_id=resume_source_artifact_id,
        )
        for artifact in self._initial_artifacts(project.id, run_id):
            run.artifacts.append(artifact)
        for log_entry in self._initial_logs():
            run.logs.append(log_entry)
        project.runs_started += 1
        project.updated_at = utcnow()
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: str) -> Optional[models.RunORM]:
        return self.db.get(models.RunORM, run_id)

    def update_run_status(
        self,
        run: models.RunORM,
        status: RunStatus,
        progress: float | None = None,
        metrics: dict[str, float] | None = None,
    ) -> models.RunORM:
        now = utcnow()
        run.status = status.value
        run.updated_at = now
        if status == RunStatus.RUNNING and run.started_at is None:
            run.started_at = now
        if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED}:
            run.completed_at = now
        if progress is not None:
            run.progress = progress
        if metrics is not None:
            run.metrics.update(metrics)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def append_run_logs(
        self, run: models.RunORM, entries: Sequence[tuple[str, str]]
    ) -> models.RunORM:
        for level, message in entries:
            log = models.RunLogORM(level=level, message=message)
            run.logs.append(log)
        run.updated_at = utcnow()
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    # Helpers
    def _initial_logs(self) -> list[models.RunLogORM]:
        messages = [
            ("INFO", "Run created"),
            ("INFO", "Initializing resources"),
            ("INFO", "Loading dataset"),
            ("INFO", "Starting training loop"),
        ]
        return [models.RunLogORM(level=level, message=message) for level, message in messages]

    def _initial_artifacts(self, project_id: str, run_id: str) -> list[models.RunArtifactORM]:
        templates = [
            ("checkpoint", "checkpoint_step_0.pt"),
            ("tensorboard", "events.out.tfevents"),
            ("config", "training_config.yaml"),
        ]
        artifacts: list[models.RunArtifactORM] = []
        for artifact_type, name in templates:
            artifacts.append(
                models.RunArtifactORM(
                    name=name,
                    type=artifact_type,
                    path=f"s3://artifacts/{project_id}/{run_id}/{name}",
                )
            )
        return artifacts
