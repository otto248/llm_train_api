"""Application entrypoint for the LLM Training Management API."""

from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import Callable, Final, Iterable

from fastapi import APIRouter, FastAPI

from app.logging import configure_logging
from src.utils.filesystem import ensure_data_directories

APP_TITLE: Final[str] = "LLM Training Management API"
APP_VERSION: Final[str] = "0.1.0"
FEATURES_PACKAGE: Final[str] = "src.features"


def _iter_feature_modules() -> Iterable[ModuleType]:
    """Yield all feature modules contained in :data:`FEATURES_PACKAGE`."""

    package = import_module(FEATURES_PACKAGE)
    for module_info in iter_modules(package.__path__, prefix=f"{package.__name__}."):
        yield import_module(module_info.name)


def _register_feature_routes(app: FastAPI) -> None:
    """Attach routers from every feature module to the FastAPI app."""

    for module in _iter_feature_modules():
        register: Callable[[FastAPI], None] | None = getattr(module, "register_routes", None)
        if callable(register):
            register(app)
            continue

        router: APIRouter | None = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""

    configure_logging()
    ensure_data_directories()
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    _register_feature_routes(application)
    return application


app = create_app()


def main() -> None:
    """Launch a development server via uvicorn."""

    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)


__all__ = ["app", "create_app", "main"]
