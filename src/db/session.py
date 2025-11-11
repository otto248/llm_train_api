"""Database engine helpers."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import metadata

_DEFAULT_DB_URL = os.getenv(
    "TRAINING_DB_URL",
    "postgresql+psycopg://app:secret123@localhost:5432/appdb",
)


def get_engine(database_url: Optional[str] = None) -> Engine:
    """Create a SQLAlchemy engine using the configured database URL."""

    return create_engine(database_url or _DEFAULT_DB_URL, future=True, pool_pre_ping=True)


def init_schema(engine: Engine) -> None:
    """Ensure that all database tables are created."""

    metadata.create_all(engine)


__all__ = ["get_engine", "init_schema"]
