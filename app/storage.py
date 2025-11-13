from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List, Optional, Sequence
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
    ProjectStatus,
    Run,
    RunDetail,
    RunStatus,
)


_DEFAULT_DB_PATH = Path(os.getenv("TRAINING_DB_PATH", "./training_data.json"))


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetimes carry UTC tzinfo."""

    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_datetime(dt: datetime) -> str:
    """Serialize datetime objects in ISO format with UTC timezone."""

    return _ensure_utc(dt).isoformat()


def _parse_datetime(raw: Optional[str]) -> Optional[datetime]:
    """Deserialize ISO datetime strings."""

    if raw is None:
        return None
    dt = datetime.fromisoformat(raw)
    return _ensure_utc(dt)


class FileStorage:
    """Lightweight file-based storage emulating the database interface."""

    def __init__(self, data_path: Optional[str] = None) -> None:
        self._path = Path(data_path) if data_path is not None else _DEFAULT_DB_PATH
        self._lock = RLock()
        self._ensure_storage_file()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ensure_storage_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(
                json.dumps(
                    {
                        "projects": {},
                        "runs": {},
                        "logs": {},
                        "artifacts": {},
                    }
                ),
                encoding="utf-8",
            )

    def _load_state(self) -> Dict[str, object]:
        with self._path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _save_state(self, state: Dict[str, object]) -> None:
        tmp_path = self._path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as fp:
            json.dump(state, fp)
        tmp_path.replace(self._path)

    def _get_project_state(self, state: Dict[str, object], project_id: str) -> Dict[str, object]:
        projects: Dict[str, Dict[str, object]] = state["projects"]  # type: ignore[assignment]
        project = projects.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found")
        return project

    def _get_run_state(self, state: Dict[str, object], run_id: str) -> Dict[str, object]:
        runs: Dict[str, Dict[str, object]] = state["runs"]  # type: ignore[assignment]
        run = runs.get(run_id)
        if run is None:
            raise KeyError(f"Run {run_id} not found")
        return run

    def _project_from_state(self, payload: Dict[str, object]) -> Project:
        return Project(
            id=payload["id"],
            name=payload["name"],
            description=payload.get("description"),
            owner=payload["owner"],
            tags=list(payload.get("tags", [])),
            dataset_name=payload["dataset_name"],
            training_yaml_name=payload["training_yaml_name"],
            status=ProjectStatus(payload["status"]),
            created_at=_parse_datetime(payload["created_at"]),
            updated_at=_parse_datetime(payload["updated_at"]),
            runs_started=payload.get("runs_started", 0),
        )

    def _artifact_from_state(self, payload: Dict[str, object]) -> Artifact:
        return Artifact(
            id=payload["id"],
            name=payload["name"],
            type=payload["type"],
            path=payload["path"],
            created_at=_parse_datetime(payload["created_at"]),
            tags=list(payload.get("tags", [])),
        )

    def _log_from_state(self, payload: Dict[str, object]) -> LogEntry:
        return LogEntry(
            timestamp=_parse_datetime(payload["timestamp"]),
            level=payload["level"],
            message=payload["message"],
        )

    def _run_from_state(
        self,
        run_payload: Dict[str, object],
        logs_payload: List[Dict[str, object]],
        artifacts_payload: List[Dict[str, object]],
    ) -> RunDetail:
        logs = [self._log_from_state(entry) for entry in sorted(
            logs_payload,
            key=lambda item: item.get("timestamp", ""),
        )]
        artifacts = [
            self._artifact_from_state(item)
            for item in sorted(
                artifacts_payload,
                key=lambda item: item.get("created_at", ""),
            )
        ]
        return RunDetail(
            id=run_payload["id"],
            project_id=run_payload["project_id"],
            status=RunStatus(run_payload["status"]),
            created_at=_parse_datetime(run_payload["created_at"]),
            updated_at=_parse_datetime(run_payload["updated_at"]),
            started_at=_parse_datetime(run_payload.get("started_at")),
            completed_at=_parse_datetime(run_payload.get("completed_at")),
            progress=run_payload.get("progress", 0.0),
            metrics=dict(run_payload.get("metrics", {})),
            start_command=run_payload["start_command"],
            artifacts=artifacts,
            logs=logs,
            resume_source_artifact_id=run_payload.get("resume_source_artifact_id"),
        )

    def _list_runs_for_project(self, state: Dict[str, object], project_id: str) -> List[RunDetail]:
        runs: Dict[str, Dict[str, object]] = state["runs"]  # type: ignore[assignment]
        logs_state: Dict[str, List[Dict[str, object]]] = state["logs"]  # type: ignore[assignment]
        artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
        project_runs = [
            run
            for run in runs.values()
            if run.get("project_id") == project_id
        ]
        project_runs.sort(key=lambda item: item.get("created_at", ""))
        return [
            self._run_from_state(
                run,
                logs_state.get(run["id"], []),
                artifacts_state.get(run["id"], []),
            )
            for run in project_runs
        ]

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------
    def create_project(self, payload: ProjectCreate) -> ProjectDetail:
        project_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)
        with self._lock:
            state = self._load_state()
            projects: Dict[str, Dict[str, object]] = state["projects"]  # type: ignore[assignment]
            if any(project["name"] == payload.name for project in projects.values()):
                raise ValueError("Project name already exists")
            project_data = {
                "id": project_id,
                "name": payload.name,
                "description": payload.description,
                "owner": payload.owner,
                "tags": list(payload.tags),
                "dataset_name": payload.dataset_name,
                "training_yaml_name": payload.training_yaml_name,
                "status": ProjectStatus.ACTIVE.value,
                "created_at": _format_datetime(timestamp),
                "updated_at": _format_datetime(timestamp),
                "runs_started": 0,
            }
            projects[project_id] = project_data
            self._save_state(state)
        return self.get_project(project_id)  # type: ignore[return-value]

    def list_projects(self) -> Iterable[Project]:
        with self._lock:
            state = self._load_state()
        projects: Dict[str, Dict[str, object]] = state["projects"]  # type: ignore[assignment]
        ordered = sorted(projects.values(), key=lambda item: item.get("created_at", ""))
        return [self._project_from_state(project) for project in ordered]

    def get_project(self, project_id: str) -> Optional[ProjectDetail]:
        with self._lock:
            state = self._load_state()
        projects: Dict[str, Dict[str, object]] = state["projects"]  # type: ignore[assignment]
        project = projects.get(project_id)
        if project is None:
            return None
        runs = self._list_runs_for_project(state, project_id)
        return ProjectDetail(**self._project_from_state(project).model_dump(), runs=runs)

    def get_project_by_name(self, project_name: str) -> Optional[ProjectDetail]:
        with self._lock:
            state = self._load_state()
        projects: Dict[str, Dict[str, object]] = state["projects"]  # type: ignore[assignment]
        for project in projects.values():
            if project.get("name") == project_name:
                runs = self._list_runs_for_project(state, project["id"])
                return ProjectDetail(
                    **self._project_from_state(project).model_dump(),
                    runs=runs,
                )
        return None

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
        timestamp = datetime.now(timezone.utc)
        with self._lock:
            state = self._load_state()
            project = self._get_project_state(state, project_id)
            runs: Dict[str, Dict[str, object]] = state["runs"]  # type: ignore[assignment]
            logs_state: Dict[str, List[Dict[str, object]]] = state["logs"]  # type: ignore[assignment]
            artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
            run_data = {
                "id": run_id,
                "project_id": project_id,
                "status": RunStatus.PENDING.value,
                "created_at": _format_datetime(timestamp),
                "updated_at": _format_datetime(timestamp),
                "started_at": None,
                "completed_at": None,
                "progress": 0.0,
                "metrics": {},
                "start_command": start_command,
                "resume_source_artifact_id": resume_source_artifact_id,
            }
            runs[run_id] = run_data
            logs_state[run_id] = self._initial_logs(timestamp)
            artifacts_state[run_id] = self._initial_artifacts(project_id, run_id, timestamp)
            project["runs_started"] = project.get("runs_started", 0) + 1
            project["updated_at"] = _format_datetime(datetime.now(timezone.utc))
            self._save_state(state)
        run = self.get_run(run_id)
        if run is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Run creation failed")
        return run

    def get_run(self, run_id: str) -> Optional[RunDetail]:
        with self._lock:
            state = self._load_state()
        runs: Dict[str, Dict[str, object]] = state["runs"]  # type: ignore[assignment]
        run_payload = runs.get(run_id)
        if run_payload is None:
            return None
        logs_state: Dict[str, List[Dict[str, object]]] = state["logs"]  # type: ignore[assignment]
        artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
        return self._run_from_state(
            run_payload,
            logs_state.get(run_id, []),
            artifacts_state.get(run_id, []),
        )

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
        now = datetime.now(timezone.utc)
        with self._lock:
            state = self._load_state()
            run = self._get_run_state(state, run_id)
            run["status"] = status.value
            run["updated_at"] = _format_datetime(now)
            if status == RunStatus.RUNNING and run.get("started_at") is None:
                run["started_at"] = _format_datetime(now)
            if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED}:
                run["completed_at"] = _format_datetime(now)
            if progress is not None:
                run["progress"] = progress
            if metrics is not None:
                current_metrics = dict(run.get("metrics", {}))
                current_metrics.update(metrics)
                run["metrics"] = current_metrics
            self._save_state(state)
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"Run {run_id} not found")
        return updated

    def append_run_logs(self, run_id: str, entries: Sequence[LogEntry]) -> RunDetail:
        if not entries:
            run = self.get_run(run_id)
            if run is None:
                raise KeyError(f"Run {run_id} not found")
            return run
        with self._lock:
            state = self._load_state()
            run = self._get_run_state(state, run_id)
            logs_state: Dict[str, List[Dict[str, object]]] = state["logs"]  # type: ignore[assignment]
            run_logs = logs_state.setdefault(run_id, [])
            for entry in entries:
                run_logs.append(
                    {
                        "timestamp": _format_datetime(entry.timestamp),
                        "level": entry.level,
                        "message": entry.message,
                    }
                )
            run["updated_at"] = _format_datetime(datetime.now(timezone.utc))
            self._save_state(state)
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"Run {run_id} not found")
        return updated

    # ------------------------------------------------------------------
    # Log operations
    # ------------------------------------------------------------------
    def get_logs(self, run_id: str, params: LogQueryParams) -> LogListResponse:
        with self._lock:
            state = self._load_state()
        logs_state: Dict[str, List[Dict[str, object]]] = state["logs"]  # type: ignore[assignment]
        run_logs = [
            self._log_from_state(entry)
            for entry in logs_state.get(run_id, [])
        ]
        run_logs.sort(key=lambda item: item.timestamp)
        filtered_logs = [
            entry
            for entry in run_logs
            if (
                (params.start_time is None or entry.timestamp >= _ensure_utc(params.start_time))
                and (params.end_time is None or entry.timestamp <= _ensure_utc(params.end_time))
            )
        ]
        start_index = (params.page - 1) * params.page_size
        end_index = start_index + params.page_size
        page_entries = filtered_logs[start_index:end_index]
        return LogListResponse(
            run_id=run_id,
            total=len(filtered_logs),
            page=params.page,
            page_size=params.page_size,
            entries=page_entries,
        )

    # ------------------------------------------------------------------
    # Artifact operations
    # ------------------------------------------------------------------
    def list_artifacts(self, run_id: str) -> ArtifactListResponse:
        with self._lock:
            state = self._load_state()
        artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
        artifacts = [
            self._artifact_from_state(entry)
            for entry in artifacts_state.get(run_id, [])
        ]
        artifacts.sort(key=lambda item: item.created_at)
        return ArtifactListResponse(run_id=run_id, artifacts=artifacts)

    def tag_artifact(
        self,
        run_id: str,
        artifact_id: str,
        payload: ArtifactTagRequest,
    ) -> Artifact:
        with self._lock:
            state = self._load_state()
            artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
            run_artifacts = artifacts_state.get(run_id, [])
            artifact = next((item for item in run_artifacts if item["id"] == artifact_id), None)
            if artifact is None:
                raise KeyError(f"Artifact {artifact_id} not found")
            tags = list(artifact.get("tags", []))
            if payload.tag not in tags:
                tags.append(payload.tag)
                artifact["tags"] = tags
                state_runs: Dict[str, Dict[str, object]] = state["runs"]  # type: ignore[assignment]
                run = state_runs.get(run_id)
                if run is not None:
                    run["updated_at"] = _format_datetime(datetime.now(timezone.utc))
            self._save_state(state)
        artifact_model = self.get_artifact(artifact_id)
        if artifact_model is None:
            raise KeyError(f"Artifact {artifact_id} not found")
        return artifact_model

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        with self._lock:
            state = self._load_state()
        artifacts_state: Dict[str, List[Dict[str, object]]] = state["artifacts"]  # type: ignore[assignment]
        for run_artifacts in artifacts_state.values():
            for artifact in run_artifacts:
                if artifact["id"] == artifact_id:
                    return self._artifact_from_state(artifact)
        return None

    # ------------------------------------------------------------------
    # Initial templates
    # ------------------------------------------------------------------
    def _initial_logs(self, timestamp: datetime) -> List[Dict[str, object]]:
        templates = [
            ("INFO", "Run created"),
            ("INFO", "Initializing resources"),
            ("INFO", "Loading dataset"),
            ("INFO", "Starting training loop"),
        ]
        return [
            {
                "id": str(uuid4()),
                "timestamp": _format_datetime(timestamp),
                "level": level,
                "message": message,
            }
            for level, message in templates
        ]

    def _initial_artifacts(
        self,
        project_id: str,
        run_id: str,
        timestamp: datetime,
    ) -> List[Dict[str, object]]:
        templates = [
            ("checkpoint", "checkpoint_step_0.pt"),
            ("tensorboard", "events.out.tfevents"),
            ("config", "training_config.yaml"),
        ]
        return [
            {
                "id": str(uuid4()),
                "run_id": run_id,
                "name": name,
                "type": artifact_type,
                "path": f"s3://artifacts/{project_id}/{run_id}/{name}",
                "created_at": _format_datetime(timestamp),
                "tags": [],
            }
            for artifact_type, name in templates
        ]


DatabaseStorage = FileStorage

storage = DatabaseStorage()

