"""Upload session management endpoints."""

from __future__ import annotations

import json
import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..models import OperationAction, OperationStatus, OperationTargetType
from ..storage import storage
from ..utils import FILES_DIR, UPLOADS_DIR, load_dataset_record, save_dataset_record

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)


@router.delete("/{upload_id}")
def abort_upload(upload_id: str) -> Dict[str, str]:
    """终止尚未完成的上传会话并清理相关文件。"""

    upload_meta_path = UPLOADS_DIR / f"{upload_id}.json"
    if not upload_meta_path.exists():
        raise HTTPException(status_code=404, detail="Upload session not found")
    with open(upload_meta_path, "r", encoding="utf-8") as file_obj:
        upload_record = json.load(file_obj)
    stored_filename = upload_record.get("stored_filename")
    if stored_filename:
        file_path = FILES_DIR / stored_filename
        if file_path.exists():
            removal_failed: OSError | None = None
            try:
                file_path.unlink()
                storage.record_operation(
                    action=OperationAction.DELETE_DATASET_FILE,
                    target_type=OperationTargetType.DATASET_FILE,
                    target_id=upload_id,
                    status=OperationStatus.SUCCESS,
                    detail="Stored dataset file removed after abort",
                    extra={
                        "stored_filename": stored_filename,
                        "dataset_id": upload_record.get("dataset_id"),
                    },
                )
            except OSError as exc:  # pragma: no cover - defensive cleanup
                removal_failed = exc
            if removal_failed is not None:
                storage.record_operation(
                    action=OperationAction.DELETE_DATASET_FILE,
                    target_type=OperationTargetType.DATASET_FILE,
                    target_id=upload_id,
                    status=OperationStatus.FAILURE,
                    detail=str(removal_failed),
                    extra={
                        "stored_filename": stored_filename,
                        "dataset_id": upload_record.get("dataset_id"),
                    },
                )
    try:
        upload_meta_path.unlink()
    except OSError as exc:  # pragma: no cover - defensive cleanup
        logger.warning("Failed to remove upload metadata %s: %s", upload_meta_path, exc)
    dataset_id = upload_record.get("dataset_id")
    if dataset_id:
        try:
            record = load_dataset_record(dataset_id)
        except FileNotFoundError:
            record = None
        if record is not None:
            original_len = len(record.get("files", []))
            record["files"] = [
                entry
                for entry in record.get("files", [])
                if entry.get("upload_id") != upload_id
            ]
            if len(record["files"]) != original_len:
                save_dataset_record(record)
    storage.record_operation(
        action=OperationAction.ABORT_UPLOAD,
        target_type=OperationTargetType.UPLOAD_SESSION,
        target_id=upload_id,
        status=OperationStatus.SUCCESS,
        detail="Upload aborted",
        extra={
            "dataset_id": dataset_id,
        },
    )
    return {"upload_id": upload_id, "status": "aborted"}
