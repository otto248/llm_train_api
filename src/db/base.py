"""SQLAlchemy metadata shared across the application."""

from __future__ import annotations

from sqlalchemy import MetaData

metadata = MetaData()

__all__ = ["metadata"]
