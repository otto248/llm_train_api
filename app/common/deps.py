from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.projects.repository import ProjectRepository
from app.api.v1.projects.service import TrainingService
from app.core.config import get_settings, Settings
from app.db.session import get_db


def get_settings_dependency() -> Settings:
    return get_settings()


def get_repository(db: Session = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


def get_training_service(
    repository: ProjectRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings_dependency),
) -> TrainingService:
    return TrainingService(repository=repository, settings=settings)
