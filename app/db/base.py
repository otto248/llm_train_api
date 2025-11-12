from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""


def configure_mappers() -> None:
    """Import models so SQLAlchemy is aware of them for Alembic autogenerate."""

    from app.api.v1.projects import models as project_models  # noqa: F401

