from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

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
    Run,
    RunCreate,
    RunDetail,
    RunStatus,
)


class InMemoryStorage:
    """Simple in-memory storage to mimic persistent behavior."""

    def __init__(self) -> None:
        self._projects: Dict[str, ProjectDetail] = {}
        self._runs: Dict[str, RunDetail] = {}

    # Project operations -------------------------------------------------
    def create_project(self, payload: ProjectCreate) -> ProjectDetail:
        project_id = str(uuid4())
        timestamp = datetime.utcnow()
        project = ProjectDetail(
            id=project_id,
            created_at=timestamp,
            updated_at=timestamp,
            runs_started=0,
            status="active",
            **payload.model_dump(),
            runs=[],
        )
        self._projects[project_id] = project
        return project

    def list_projects(self) -> Iterable[Project]:
        return [Project(**project.model_dump(exclude={"runs"})) for project in self._projects.values()]

    def get_project(self, project_id: str) -> Optional[ProjectDetail]:
        return self._projects.get(project_id)

    # Run operations -----------------------------------------------------
    def _build_run(
        self,
        project_id: str,
        payload: RunCreate,
        resume_source_artifact_id: Optional[str] = None,
    ) -> RunDetail:
        run_id = str(uuid4())
        timestamp = datetime.utcnow()
        run = RunDetail(
            id=run_id,
            project_id=project_id,
            status=RunStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
            started_at=None,
            completed_at=None,
            progress=0.0,
            metrics={},
            start_command=payload.start_command,
            artifacts=[],
            logs=[],
            resume_source_artifact_id=resume_source_artifact_id,
        )
        return run

    def create_run(
        self,
        project_id: str,
        payload: RunCreate,
        resume_source_artifact_id: Optional[str] = None,
    ) -> RunDetail:
        project = self._projects[project_id]
        run = self._build_run(project_id, payload, resume_source_artifact_id)
        project.runs.append(run)
        project.runs_started += 1
        project.updated_at = datetime.utcnow()
        self._runs[run.id] = run
        self._generate_initial_artifacts(run)
        self._generate_initial_logs(run)
        return run

    def get_run(self, run_id: str) -> Optional[RunDetail]:
        return self._runs.get(run_id)

    def iter_project_runs(self, project_id: str) -> Iterable[RunDetail]:
        return self._projects[project_id].runs

    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        progress: Optional[float] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> RunDetail:
        run = self._runs[run_id]
        run.status = status
        now = datetime.utcnow()
        run.updated_at = now
        if status == RunStatus.RUNNING and run.started_at is None:
            run.started_at = now
        if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED}:
            run.completed_at = now
        if progress is not None:
            run.progress = progress
        if metrics is not None:
            run.metrics.update(metrics)
        return run

    def cancel_run(self, run_id: str) -> RunDetail:
        run = self._runs[run_id]
        if run.status not in {RunStatus.CANCELED, RunStatus.COMPLETED, RunStatus.FAILED}:
            run.status = RunStatus.CANCELED
            run.updated_at = datetime.utcnow()
            run.completed_at = run.completed_at or datetime.utcnow()
        return run

    # Log operations -----------------------------------------------------
    def _filter_logs(self, logs: List[LogEntry], params: LogQueryParams) -> List[LogEntry]:
        filtered = logs
        if params.start_time:
            filtered = [log for log in filtered if log.timestamp >= params.start_time]
        if params.end_time:
            filtered = [log for log in filtered if log.timestamp <= params.end_time]
        return filtered

    def get_logs(self, run_id: str, params: LogQueryParams) -> LogListResponse:
        run = self._runs[run_id]
        filtered = self._filter_logs(run.logs, params)
        start_index = (params.page - 1) * params.page_size
        end_index = start_index + params.page_size
        entries = filtered[start_index:end_index]
        return LogListResponse(
            run_id=run_id,
            total=len(filtered),
            page=params.page,
            page_size=params.page_size,
            entries=entries,
        )

    # Artifact operations ------------------------------------------------
    def list_artifacts(self, run_id: str) -> ArtifactListResponse:
        run = self._runs[run_id]
        return ArtifactListResponse(run_id=run_id, artifacts=run.artifacts)

    def tag_artifact(self, run_id: str, artifact_id: str, payload: ArtifactTagRequest) -> Artifact:
        run = self._runs[run_id]
        artifact = next(art for art in run.artifacts if art.id == artifact_id)
        if payload.tag not in artifact.tags:
            artifact.tags.append(payload.tag)
        run.updated_at = datetime.utcnow()
        return artifact

    # Helper methods -----------------------------------------------------
    def _generate_initial_logs(self, run: RunDetail) -> None:
        now = datetime.utcnow()
        template = [
            ("INFO", "Run created"),
            ("INFO", "Initializing resources"),
            ("INFO", "Loading dataset"),
            ("INFO", "Starting training loop"),
        ]
        run.logs.extend(
            LogEntry(timestamp=now, level=level, message=message)
            for level, message in template
        )

    def _generate_initial_artifacts(self, run: RunDetail) -> None:
        now = datetime.utcnow()
        artifact_templates = [
            ("checkpoint", "checkpoint_step_0.pt"),
            ("tensorboard", "events.out.tfevents"),
            ("config", "training_config.yaml"),
        ]
        run.artifacts.extend(
            Artifact(
                id=str(uuid4()),
                name=name,
                type=artifact_type,
                path=f"s3://artifacts/{run.project_id}/{run.id}/{name}",
                created_at=now,
                tags=[],
            )
            for artifact_type, name in artifact_templates
        )

    def resume_run(
        self,
        project_id: str,
        run_id: str,
        payload: RunCreate,
        source_artifact_id: str,
    ) -> RunDetail:
        return self.create_run(
            project_id=project_id,
            payload=payload,
            resume_source_artifact_id=source_artifact_id,
        )


storage = InMemoryStorage()
