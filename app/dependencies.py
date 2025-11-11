"""Shared dependency definitions for FastAPI routers."""

from __future__ import annotations

from .storage import DatabaseStorage, storage


def get_storage() -> DatabaseStorage:
    """Provide the singleton database storage instance for request handlers."""

    return storage
