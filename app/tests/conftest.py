from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.v1.projects.repository import ProjectRepository
from app.api.v1.projects.service import TrainingService
from app.core.config import Settings
from app.db.base import Base, configure_mappers


@pytest.fixture()
def engine(tmp_path: Path):
    configure_mappers()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'training.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def repository(db_session: Session) -> ProjectRepository:
    return ProjectRepository(db_session)


@pytest.fixture()
def settings() -> Settings:
    return Settings(enable_process_launch=False, host_training_dir=None)


@pytest.fixture()
def service(repository: ProjectRepository, settings: Settings) -> TrainingService:
    return TrainingService(repository=repository, settings=settings)
