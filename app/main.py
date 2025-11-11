from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import shlex
import subprocess
import uuid
import re
import random
from pathlib import Path as PathlibPath
from typing import Any, Dict, List

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Path as PathParam,
    UploadFile,
)

from .models import (
    ContainerFileRequest,
    ContainerFileResponse,
    LogEntry,
    Project,
    ProjectCreate,
    ProjectDetail,
    Run,
    RunDetail,
    RunStatus,
    DeidRequest,
    DeidResponse,
    DatasetCreateRequest,
    DatasetRecord,
)
from .storage import DatabaseStorage, storage
from .utils import (
    FILES_DIR,
    TRAIN_CONFIG_DIR,
    UPLOADS_DIR,
    ensure_data_directories,
    load_dataset_record,
    save_dataset_record,
)

app = FastAPI(title="LLM Training Management API", version="0.1.0")
logger = logging.getLogger(__name__)


_HOST_TRAINING_DIR = "/data1/qwen2.5-14bxxxx"
_DOCKER_CONTAINER_NAME = "qwen2.5-14b-instruct_xpytorch_full_sft"
_DOCKER_WORKING_DIR = "KTIP_Release_2.1.0/train/llm"

_CONTAINER_FILE_TARGET_DIR = "/mnt/disk"
_CONTAINER_FILE_CONTENT = "cym"
_LOCAL_DOCKER_CONTAINER_NAME = "mycontainer"


_HOST_TRAINING_PATH = PathlibPath(_HOST_TRAINING_DIR).resolve()

ensure_data_directories()

MAX_SMALL_FILE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_YAML_BYTES = 5 * 1024 * 1024  # 5MB
POLICY_VERSION = "2024-01-01"


class DeidStrategy:
    """抽象基类：定义脱敏策略接口。"""

    def deidentify_texts(
        self, texts: List[str], options: Dict[str, Any]
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        raise NotImplementedError


STRATEGY_REGISTRY: Dict[str, DeidStrategy] = {}


def register_strategy(name: str):
    def deco(cls: type[DeidStrategy]) -> type[DeidStrategy]:
        STRATEGY_REGISTRY[name] = cls()
        return cls

    return deco


@register_strategy("default")
class RandomDigitReplacement(DeidStrategy):
    """默认脱敏策略：把数字替换为随机数字，支持 seed 控制。"""

    digit_re = re.compile(r"\d+")

    def deidentify_texts(
        self, texts: List[str], options: Dict[str, Any]
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        seed = options.get("seed")
        rng = random.Random(seed)
        mapping: Dict[str, str] = {}

        def _replace(match: re.Match[str]) -> str:
            original = match.group(0)
            if original in mapping:
                return mapping[original]
            replacement = "".join(str(rng.randint(0, 9)) for _ in original)
            mapping[original] = replacement
            return replacement

        deidentified_texts: List[str] = []
        for text in texts:
            deidentified_texts.append(self.digit_re.sub(_replace, text))

        mapping_list = [
            {"type": "NUMBER", "original": original, "pseudo": pseudo}
            for original, pseudo in mapping.items()
        ]
        return deidentified_texts, mapping_list


def _launch_training_process(start_command: str) -> subprocess.Popen[bytes]:
    """在目标 Docker 容器内启动远程训练命令。"""

    docker_command = (
        f"cd {_HOST_TRAINING_DIR} && "
        f"docker exec -i {_DOCKER_CONTAINER_NAME} "
        "env LANG=C.UTF-8 bash -lc "
        f"\"cd {_DOCKER_WORKING_DIR} && {start_command}\""
    )
    logger.info("Launching training command: %s", docker_command)
    try:
        process = subprocess.Popen(  # noqa: S603, S607 - intentional command execution
            ["bash", "-lc", docker_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("无法执行训练命令，请检查服务器环境配置。") from exc
    return process


def _run_container_command(container_name: str, command: str) -> None:
    docker_command = [
        "docker",
        "exec",
        "-i",
        container_name,
        "bash",
        "-lc",
        command,
    ]
    result = subprocess.run(  # noqa: S603, S607 - intentional command execution
        docker_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error(
            "Failed to run command in container %s: %s", container_name, stderr
        )
        raise RuntimeError(
            f"无法在容器 {container_name} 中执行命令：{stderr or '未知错误'}"
        )


def get_storage() -> DatabaseStorage:
    return storage


def _build_start_command(project: ProjectDetail) -> str:
    return f"bash run_train_full_sft.sh {project.training_yaml_name}"


def _resolve_project_asset(relative_path: str) -> PathlibPath:
    candidate = (_HOST_TRAINING_PATH / relative_path).resolve()
    try:
        candidate.relative_to(_HOST_TRAINING_PATH)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"资源路径无效：仅允许访问位于 {_HOST_TRAINING_PATH} 下的文件或目录。"
            ),
        ) from exc
    return candidate


def _create_file_in_container(filename: str) -> str:
    sanitized = PathlibPath(filename).name
    if sanitized != filename:
        raise HTTPException(status_code=400, detail="文件名非法，仅允许提供文件名。")
    if sanitized in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不能为空或特殊目录。")
    target_path = f"{_CONTAINER_FILE_TARGET_DIR}/{sanitized}"
    shell_command = (
        f"mkdir -p {_CONTAINER_FILE_TARGET_DIR} && "
        f"printf %s {shlex.quote(_CONTAINER_FILE_CONTENT)} > {shlex.quote(target_path)}"
    )
    try:
        _run_container_command(_LOCAL_DOCKER_CONTAINER_NAME, shell_command)
    except RuntimeError as exc:  # pragma: no cover - depends on runtime environment
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return target_path


def _get_project_by_reference(
    project_reference: str, store: DatabaseStorage
) -> ProjectDetail:
    project = store.get_project(project_reference)
    if project is None:
        project = store.get_project_by_name(project_reference)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_project_assets_available(project: ProjectDetail) -> None:
    missing: List[str] = []
    dataset_path = _resolve_project_asset(project.dataset_name)
    if not dataset_path.exists():
        missing.append(f"数据集 {project.dataset_name}")
    yaml_path = _resolve_project_asset(project.training_yaml_name)
    if not yaml_path.exists():
        missing.append(f"训练配置 {project.training_yaml_name}")
    if missing:
        raise HTTPException(
            status_code=400,
            detail="以下项目资源尚未上传完成：" + "、".join(missing),
        )


@app.post("/projects", response_model=ProjectDetail, status_code=201)
def create_project(
    payload: ProjectCreate, store: DatabaseStorage = Depends(get_storage)
) -> ProjectDetail:
    """创建新的训练项目（功能点 5.2.1）。"""

    project = store.create_project(payload)
    return project


@app.get("/projects", response_model=List[Project])
def list_projects(store: DatabaseStorage = Depends(get_storage)) -> List[Project]:
    """列出所有训练项目。"""

    return list(store.list_projects())


@app.post("/projects/{project_reference}/runs", response_model=RunDetail, status_code=201)
def create_run(
    project_reference: str = PathParam(
        ..., description="Project identifier or unique name"
    ),
    store: DatabaseStorage = Depends(get_storage),
) -> RunDetail:
    """在指定项目下启动新的训练运行（功能点 5.2.3）。"""

    project = _get_project_by_reference(project_reference, store)
    _ensure_project_assets_available(project)
    start_command = _build_start_command(project)
    run = store.create_run(project.id, start_command)
    run = store.append_run_logs(
        run.id,
        [
            LogEntry(
                timestamp=datetime.utcnow(),
                level="INFO",
                message=(
                    "已确认训练资源数据集 "
                    f"{project.dataset_name}，配置 {project.training_yaml_name}"
                ),
            )
        ],
    )
    try:
        process = _launch_training_process(start_command)
    except RuntimeError as exc:
        store.append_run_logs(
            run.id,
            [
                LogEntry(
                    timestamp=datetime.utcnow(),
                    level="ERROR",
                    message=str(exc),
                )
            ],
        )
        store.update_run_status(run.id, RunStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    store.append_run_logs(
        run.id,
        [
            LogEntry(
                timestamp=datetime.utcnow(),
                level="INFO",
                message=(f"已触发训练命令：{start_command} (PID {process.pid})"),
            )
        ],
    )
    run = store.update_run_status(run.id, RunStatus.RUNNING, progress=0.05)
    return run


@app.post(
    "/containers/mycontainer/files",
    response_model=ContainerFileResponse,
    status_code=201,
)
def create_container_file(
    payload: ContainerFileRequest = Body(ContainerFileRequest()),
) -> ContainerFileResponse:
    """在指定容器的 /mnt/disk 目录下创建文件并写入固定内容。"""

    file_path = _create_file_in_container(payload.filename)
    return ContainerFileResponse(path=file_path, content=_CONTAINER_FILE_CONTENT)


@app.post("/v1/deidentify:test", response_model=DeidResponse)
def deidentify(req: DeidRequest) -> DeidResponse:
    policy_id = req.policy_id or "default"
    strategy = STRATEGY_REGISTRY.get(policy_id)
    if strategy is None:
        raise HTTPException(status_code=400, detail=f"Unknown policy_id '{policy_id}'")
    options = req.options.model_dump() if req.options else {}
    deid_texts, mapping_list = strategy.deidentify_texts(req.text, options)
    mapping: List[Dict[str, str]] | None = mapping_list if options.get("return_mapping") else None
    return DeidResponse(
        deidentified=deid_texts,
        mapping=mapping,
        policy_version=POLICY_VERSION,
    )


@app.post("/v1/datasets")
def create_dataset(req: DatasetCreateRequest) -> Dict[str, str]:
    dataset_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    record = DatasetRecord(
        id=dataset_id,
        name=req.name,
        type=req.dtype,
        source=req.source,
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
    return {"id": dataset_id, "created_at": created_at}


@app.get("/v1/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> Dict[str, Any]:
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    record.setdefault("files", [])
    record.setdefault("train_config", None)
    record["upload_progress"] = {"files_count": len(record["files"])}
    return record


@app.put("/v1/datasets/{dataset_id}/files")
async def upload_small_file(dataset_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
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
    return {
        "upload_id": upload_id,
        "dataset_id": dataset_id,
        "bytes": size,
        "filename": file.filename,
    }


@app.delete("/v1/uploads/{upload_id}")
def abort_upload(upload_id: str) -> Dict[str, str]:
    upload_meta_path = UPLOADS_DIR / f"{upload_id}.json"
    if not upload_meta_path.exists():
        raise HTTPException(status_code=404, detail="Upload session not found")
    with open(upload_meta_path, "r", encoding="utf-8") as file_obj:
        upload_record = json.load(file_obj)
    stored_filename = upload_record.get("stored_filename")
    if stored_filename:
        file_path = FILES_DIR / stored_filename
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to remove stored file %s: %s", file_path, exc)
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
                entry for entry in record.get("files", []) if entry.get("upload_id") != upload_id
            ]
            if len(record["files"]) != original_len:
                save_dataset_record(record)
    return {"upload_id": upload_id, "status": "aborted"}


@app.put("/v1/datasets/{dataset_id}/train-config")
async def upload_train_config(dataset_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    if not (file.filename.endswith(".yaml") or file.filename.endswith(".yml")):
        raise HTTPException(status_code=400, detail="Only .yaml or .yml files are allowed")
    content = await file.read()
    if len(content) > MAX_YAML_BYTES:
        raise HTTPException(
            status_code=413,
            detail="YAML file too large (max 5MB)",
        )
    config_path = TRAIN_CONFIG_DIR / f"{dataset_id}_train.yaml"
    with open(config_path, "wb") as file_obj:
        file_obj.write(content)
    uploaded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"
    record["train_config"] = {
        "filename": file.filename,
        "uploaded_at": uploaded_at,
        "size": len(content),
    }
    record["status"] = "train_config_uploaded"
    save_dataset_record(record)
    return {"dataset_id": dataset_id, "train_config": record["train_config"]}


@app.get("/v1/datasets/{dataset_id}/train-config")
def get_train_config(dataset_id: str) -> Dict[str, Any]:
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    train_config = record.get("train_config")
    if not train_config:
        raise HTTPException(status_code=404, detail="Train config not uploaded yet")
    return train_config


@app.delete("/v1/datasets/{dataset_id}/train-config")
def delete_train_config(dataset_id: str) -> Dict[str, str]:
    try:
        record = load_dataset_record(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset not found") from exc
    config_path = TRAIN_CONFIG_DIR / f"{dataset_id}_train.yaml"
    if config_path.exists():
        try:
            config_path.unlink()
        except OSError as exc:  # pragma: no cover - best-effort cleanup
            logger.warning("Failed to remove train config %s: %s", config_path, exc)
    record["train_config"] = None
    record["status"] = "train_config_deleted"
    save_dataset_record(record)
    return {"dataset_id": dataset_id, "status": "train_config_deleted"}


@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}
