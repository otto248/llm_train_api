from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Path, Query

from .models import (
    Artifact,
    ArtifactListResponse,
    ArtifactTagRequest,
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
from .storage import InMemoryStorage, storage

app = FastAPI(title="LLM Training Management API", version="0.1.0")


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


@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: str = Path(..., description="Project identifier"),
    store: InMemoryStorage = Depends(get_storage),
) -> ProjectDetail:
    """Retrieve detailed information about a project (5.2.2)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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
    store.update_run_status(run.id, RunStatus.RUNNING, progress=0.05)
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


@app.get("/projects/{project_id}/runs/{run_id}/logs", response_model=LogListResponse)
def get_run_logs(
    project_id: str,
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    store: InMemoryStorage = Depends(get_storage),
) -> LogListResponse:
    """Fetch paginated run logs (5.2.6)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    params = LogQueryParams(page=page, page_size=page_size, start_time=start_time, end_time=end_time)
    return store.get_logs(run_id, params)


@app.get("/projects/{project_id}/runs/{run_id}/artifacts", response_model=ArtifactListResponse)
def get_run_artifacts(
    project_id: str,
    run_id: str,
    store: InMemoryStorage = Depends(get_storage),
) -> ArtifactListResponse:
    """List artifacts produced by a run (5.2.7)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return store.list_artifacts(run_id)


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


@app.post(
    "/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/tag",
    response_model=Artifact,
)
def tag_artifact(
    payload: ArtifactTagRequest,
    project_id: str,
    run_id: str,
    artifact_id: str,
    store: InMemoryStorage = Depends(get_storage),
) -> Artifact:
    """Mark a checkpoint as candidate or release (5.2.9)."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = store.get_run(run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    artifact = next((art for art in run.artifacts if art.id == artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return store.tag_artifact(run_id, artifact_id, payload)
