from __future__ import annotations

from datetime import datetime
import logging
import subprocess
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Path, Query

from .models import (
    LogEntry,
    Project,
    ProjectCreate,
    ProjectDetail,
    Run,
    RunCreate,
    RunDetail,
    RunStatus,
)
from .storage import InMemoryStorage, storage

app = FastAPI(title="LLM Training Management API", version="0.1.0")
logger = logging.getLogger(__name__)


_HOST_TRAINING_DIR = "/data1/qwen2.5-14bxxxx"
_DOCKER_CONTAINER_NAME = "qwen2.5-14b-instruct_xpytorch_full_sft"
_DOCKER_WORKING_DIR = "KTIP_Release_2.1.0/train/llm"


def _launch_training_process(training_yaml_name: str) -> subprocess.Popen[bytes]:
    """Kick off the remote training command inside the target Docker container."""

    docker_command = (
        f"cd {_HOST_TRAINING_DIR} && "
        f"docker exec -i {_DOCKER_CONTAINER_NAME} "
        "env LANG=C.UTF-8 bash -lc "
        f"\"cd {_DOCKER_WORKING_DIR} && bash run_train_full_sft.sh {training_yaml_name}\""
    )
    logger.info("Launching training command: %s", docker_command)
    try:
        process = subprocess.Popen(  # noqa: S603, S607 - intentional command execution
            ["bash", "-lc", docker_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("无法执行训练命令，请检查服务器环境配置。") from exc
    return process


def get_storage() -> InMemoryStorage:
    return storage


@app.post("/projects", response_model=ProjectDetail, status_code=201)
def create_project(payload: ProjectCreate, store: InMemoryStorage = Depends(get_storage)) -> ProjectDetail:
    """Create a new training project (5.2.1)."""
    project = store.create_project(payload)
    return project


@app.get("/projects", response_model=List[Project])
def list_projects(store: InMemoryStorage = Depends(get_storage)) -> List[Project]:
    """List all training projects."""
    return list(store.list_projects())


@app.post("/projects/{project_id}/runs", response_model=RunDetail, status_code=201)
def create_run(
    payload: RunCreate,
    project_id: str = Path(..., description="Project identifier"),
    store: InMemoryStorage = Depends(get_storage),
) -> RunDetail:
    """Start a new training run under a project (5.2.3)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.create_run(project_id, payload)
    try:
        process = _launch_training_process(project.training_yaml_name)
    except RuntimeError as exc:
        run.logs.append(
            LogEntry(
                timestamp=datetime.utcnow(),
                level="ERROR",
                message=str(exc),
            )
        )
        store.update_run_status(run.id, RunStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    run.logs.append(
        LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            message=(
                "已触发训练命令：bash run_train_full_sft.sh "
                f"{project.training_yaml_name} (PID {process.pid})"
            ),
        )
    )
    run = store.update_run_status(run.id, RunStatus.RUNNING, progress=0.05)
    return run


@app.get("/projects/{project_id}/runs/{run_id}", response_model=RunDetail)
def get_run(
    project_id: str = Path(..., description="Project identifier"),
    run_id: str = Path(..., description="Run identifier"),
    store: InMemoryStorage = Depends(get_storage),
) -> RunDetail:
    """Retrieve the status and metrics of a run (5.2.4)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/projects/{project_id}/runs/{run_id}/cancel", response_model=RunDetail)
def cancel_run(
    project_id: str,
    run_id: str,
    store: InMemoryStorage = Depends(get_storage),
) -> RunDetail:
    """Cancel an active run (5.2.5)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return store.cancel_run(run_id)


@app.post("/projects/{project_id}/runs/{run_id}/resume", response_model=RunDetail, status_code=201)
def resume_run(
    payload: RunCreate,
    project_id: str,
    run_id: str,
    source_artifact_id: str = Query(..., description="Checkpoint artifact to resume from"),
    store: InMemoryStorage = Depends(get_storage),
) -> RunDetail:
    """Resume a run from a checkpoint (5.2.8)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = next((artifact for artifact in run.artifacts if artifact.id == source_artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Checkpoint artifact not found")
    resumed_run = store.resume_run(project_id, run_id, payload, source_artifact_id)
    store.update_run_status(resumed_run.id, RunStatus.RUNNING, progress=0.05)
    return resumed_run


