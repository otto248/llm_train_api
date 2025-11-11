"""Training configuration upload endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile

from ..config import MAX_YAML_BYTES
from ..models import OperationAction, OperationStatus, OperationTargetType
from ..storage import storage
from ..utils import (
    delete_train_config_metadata,
    load_train_config_metadata,
    save_train_config_metadata,
    train_config_path,
)

router = APIRouter(prefix="/v1/train-config", tags=["train-config"])
logger = logging.getLogger(__name__)


@router.put("")
async def upload_train_config(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传训练配置文件并记录元数据。"""

    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        raise HTTPException(status_code=400, detail="Only .yaml or .yml files are allowed")
    content = await file.read()
    if len(content) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=413,
            detail="YAML file too large (max 5MB)",
        )
    config_path = train_config_path()
    with open(config_path, "wb") as file_obj:
        file_obj.write(content)
    uploaded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    metadata = {
        "filename": file.filename,
        "uploaded_at": uploaded_at,
        "size": len(content),
    }
    save_train_config_metadata(metadata)
    storage.record_operation(
        action=OperationAction.UPLOAD_TRAIN_CONFIG,
        target_type=OperationTargetType.TRAIN_CONFIG,
        target_id=file.filename,
        status=OperationStatus.SUCCESS,
        detail="Training YAML uploaded",
        extra={"size": len(content)},
    )
    return {"train_config": metadata}


@router.get("")
def get_train_config() -> Dict[str, Any]:
    """读取训练配置的元数据，不存在时返回 404。"""

    try:
        return load_train_config_metadata()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Train config not uploaded yet") from exc


@router.delete("")
def delete_train_config() -> Dict[str, str]:
    """删除训练配置文件及元数据，并记录操作结果。"""

    config_path = train_config_path()
    file_was_present = config_path.exists()
    removal_error: OSError | None = None
    if file_was_present:
        try:
            config_path.unlink()
        except OSError as exc:  # pragma: no cover - best-effort cleanup
            removal_error = exc
            logger.warning("Failed to remove train config %s: %s", config_path, exc)
    delete_train_config_metadata()
    if removal_error is not None:
        storage.record_operation(
            action=OperationAction.DELETE_TRAIN_CONFIG,
            target_type=OperationTargetType.TRAIN_CONFIG,
            target_id=config_path.name,
            status=OperationStatus.FAILURE,
            detail=str(removal_error),
            extra={"file_was_present": file_was_present},
        )
    else:
        storage.record_operation(
            action=OperationAction.DELETE_TRAIN_CONFIG,
            target_type=OperationTargetType.TRAIN_CONFIG,
            target_id=config_path.name,
            status=OperationStatus.SUCCESS,
            detail="Training YAML deleted",
            extra={"file_was_present": file_was_present},
        )
    return {"status": "train_config_deleted"}


def register_routes(app: FastAPI) -> None:
    """Register training configuration endpoints on the provided application."""

    app.include_router(router)


__all__ = ["router", "register_routes"]
