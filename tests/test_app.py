"""Smoke tests for the FastAPI application factory."""

import os
import sys
import types

os.environ.setdefault("TRAINING_DB_URL", "sqlite+pysqlite:///:memory:")

multipart_stub = types.ModuleType("multipart")
multipart_stub.__version__ = "0.0"
sys.modules.setdefault("multipart", multipart_stub)

multipart_submodule = types.ModuleType("multipart.multipart")
multipart_submodule.parse_options_header = lambda value: None  # type: ignore[attr-defined]
sys.modules.setdefault("multipart.multipart", multipart_submodule)

from app.main import create_app


def test_create_app_registers_routes() -> None:
    app = create_app()
    assert any(route.path == "/_internal/health" for route in app.routes)
