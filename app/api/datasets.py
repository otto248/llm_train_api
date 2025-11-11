"""Dataset management API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import MAX_SMALL_FILE_BYTES
from ..models import (
    DatasetCreateRequest,
    DatasetRecord,
    OperationAction,
    OperationStatus,
    OperationTargetType,
)
from ..storage import storage
from ..utils import FILES_DIR, UPLOADS_DIR, load_dataset_record, save_dataset_record

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])


@router.post("")
def create_dataset(req: DatasetCreateRequest) -> Dict[str, str]:
    """创建新的数据集元数据并记录操作日志。"""
    dataset_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    record = DatasetRecord(
        id=dataset_id,
        name=req.name,
        type=req.dtype,
        description=req.description,
        task_type=req.task_type,
        metadata=req.metadata or {},
        created_at=created_at,
        status="created",
        files=[],
    )
    record_dict = record.model_dump()
    record_dict["metadata"] = record_dict.get("metadata") or {}
    record_dict.setdefault("train_config", None)
    save_dataset_record(record_dict)
    storage.record_operation(
        action=OperationAction.CREATE_DATASET,
        target_type=OperationTargetType.DATASET,
        target_id=dataset_id,
        status=OperationStatus.SUCCESS,
        detail="Dataset metadata created",
        extra={
            "name": req.name,
            "task_type": req.task_type,
        },
    )
    return {"id": dataset_id, "created_at": created_at}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> Dict[str, Any]:
    """读取指定数据集的详细信息，如果不存在则返回 404。"""
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    record.setdefault("files", [])
    record.setdefault("train_config", None)
    record["upload_progress"] = {"files_count": len(record["files"])}
    return record


@router.put("/{dataset_id}/files")
async def upload_small_file(dataset_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传小文件到数据集并更新文件记录与上传日志。"""
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    content = await file.read()
    size = len(content)
    if size > MAX_SMALL_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Limit is {MAX_SMALL_FILE_BYTES} bytes",
        )
    upload_id = str(uuid.uuid4())
    filename = f"{upload_id}_{file.filename}"
    file_path = FILES_DIR / filename
    with open(file_path, "wb") as file_obj:
        file_obj.write(content)
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    upload_record = {
        "upload_id": upload_id,
        "dataset_id": dataset_id,
        "filename": file.filename,
        "stored_filename": filename,
        "bytes": size,
        "created_at": created_at,
        "status": "completed",
    }
    with open(UPLOADS_DIR / f"{upload_id}.json", "w", encoding="utf-8") as file_obj:
        json.dump(upload_record, file_obj, ensure_ascii=False, indent=2)
    file_entry = {
        "upload_id": upload_id,
        "name": file.filename,
        "stored_name": filename,
        "bytes": size,
        "uploaded_at": created_at,
    }
    record.setdefault("files", []).append(file_entry)
    record["status"] = "ready"
    save_dataset_record(record)
    storage.record_operation(
        action=OperationAction.UPLOAD_DATASET_FILE,
        target_type=OperationTargetType.DATASET_FILE,
        target_id=upload_id,
        status=OperationStatus.SUCCESS,
        detail="Dataset file uploaded",
        extra={
            "dataset_id": dataset_id,
            "filename": file.filename,
            "bytes": size,
        },
    )
    return {
        "upload_id": upload_id,
        "dataset_id": dataset_id,
        "bytes": size,
        "filename": file.filename,
    }


