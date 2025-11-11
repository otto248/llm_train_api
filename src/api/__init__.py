"""Router registration utilities for the training API."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable

from fastapi import FastAPI

_ROUTER_MODULES: Iterable[str] = (
    "src.api.health",
    "src.api.datasets",
    "src.api.train_configs",
    "src.api.projects",
    "src.api.deidentify",
    "src.api.deployments",
)


def register_routers(app: FastAPI) -> None:
    """Import each router module and call its ``register_routes`` helper."""

    for module_path in _ROUTER_MODULES:
        module = import_module(module_path)
        register = getattr(module, "register_routes", None)
        if register is None:
            raise AttributeError(f"Module {module_path} is missing register_routes()")
        register(app)


__all__ = ["register_routers"]
