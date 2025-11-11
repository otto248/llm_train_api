"""API registration helpers exposed at the package level."""

from __future__ import annotations

from .dataset_upload import register_routes as register_dataset_routes
from .deid import register_routes as register_deid_routes
from .deployment import register_routes as register_deployment_routes
from .health import register_routes as register_health_routes
from .project import register_routes as register_project_routes
from .train_config import register_routes as register_train_config_routes

__all__ = [
    "register_dataset_routes",
    "register_deid_routes",
    "register_deployment_routes",
    "register_health_routes",
    "register_project_routes",
    "register_train_config_routes",
]
