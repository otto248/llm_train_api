from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.v1.projects.schemas import ProjectCreate, ProjectDetail, Project, RunDetail
from app.api.v1.projects.service import TrainingService
from app.common.deps import get_training_service

router = APIRouter()


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    service: TrainingService = Depends(get_training_service),
) -> ProjectDetail:
    return service.create_project(payload)


@router.get("", response_model=list[Project])
def list_projects(service: TrainingService = Depends(get_training_service)) -> list[Project]:
    return service.list_projects()


@router.post("/{project_reference}/runs", response_model=RunDetail, status_code=status.HTTP_201_CREATED)
def create_run(
    project_reference: str,
    service: TrainingService = Depends(get_training_service),
) -> RunDetail:
    return service.create_run(project_reference)
