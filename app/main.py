"""Compatibility shim that re-exports the root application factory."""

from __future__ import annotations

from main import app, create_app, main as run

__all__ = ["app", "create_app", "run"]
