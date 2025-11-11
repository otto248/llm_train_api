"""Router registration utilities for the training API."""

from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType
from typing import Iterable

from fastapi import FastAPI


def _discover_router_modules() -> Iterable[ModuleType]:
    """Yield all router modules defined under ``src.api``.

    This keeps ``app/main.py`` simple and ensures that adding a new feature
    endpoint only requires creating a module with a ``register_routes`` helper.
    """

    package_name = __name__
    for module_info in iter_modules(__path__):
        if module_info.ispkg or module_info.name.startswith("_"):
            continue
        yield import_module(f"{package_name}.{module_info.name}")


def register_routers(app: FastAPI) -> None:
    """Import each router module and call its ``register_routes`` helper."""

    for module in _discover_router_modules():
        register = getattr(module, "register_routes", None)
        if register is None:
            raise AttributeError(
                f"Module {module.__name__} is missing register_routes()"
            )
        register(app)


__all__ = ["register_routers"]
