from __future__ import annotations

from datetime import datetime
import logging
import subprocess
from typing import List
from pathlib import Path as PathlibPath

from fastapi import Depends, FastAPI, HTTPException, Path as PathParam

from .models import (
    LogEntry,
    Project,
    ProjectCreate,
    ProjectDetail,
    Run,
    RunDetail,
    RunStatus,
)
from .storage import InMemoryStorage, storage

app = FastAPI(title="LLM Training Management API", version="0.1.0")
logger = logging.getLogger(__name__)


_HOST_TRAINING_DIR = "/data1/qwen2.5-14bxxxx"
_DOCKER_CONTAINER_NAME = "qwen2.5-14b-instruct_xpytorch_full_sft"
_DOCKER_WORKING_DIR = "KTIP_Release_2.1.0/train/llm"


_HOST_TRAINING_PATH = PathlibPath(_HOST_TRAINING_DIR).resolve()


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


def get_storage() -> InMemoryStorage:
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


def _get_project_by_reference(
    project_reference: str, store: InMemoryStorage
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
def create_project(payload: ProjectCreate, store: InMemoryStorage = Depends(get_storage)) -> ProjectDetail:
    """创建新的训练项目（功能点 5.2.1）。"""
    project = store.create_project(payload)
    return project


@app.get("/projects", response_model=List[Project])
def list_projects(store: InMemoryStorage = Depends(get_storage)) -> List[Project]:
    """列出所有训练项目。"""
    return list(store.list_projects())


@app.post("/projects/{project_reference}/runs", response_model=RunDetail, status_code=201)
def create_run(
    project_reference: str = PathParam(
        ..., description="Project identifier or unique name"
    ),
    store: InMemoryStorage = Depends(get_storage),
) -> RunDetail:
    """在指定项目下启动新的训练运行（功能点 5.2.3）。"""
    project = _get_project_by_reference(project_reference, store)
    _ensure_project_assets_available(project)
    start_command = _build_start_command(project)
    run = store.create_run(project.id, start_command)
    run.logs.append(
        LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            message=(
                "已确认训练资源数据集 "
                f"{project.dataset_name}，配置 {project.training_yaml_name}"
            ),
        )
    )
    try:
        process = _launch_training_process(start_command)
    except RuntimeError as exc:
        run.logs.append(
            LogEntry(
                timestamp=datetime.utcnow(),
                level="ERROR",
                message=str(exc),
            )
        )
        store.update_run_status(run.id, RunStatus.FAILED)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    run.logs.append(
        LogEntry(
            timestamp=datetime.utcnow(),
            level="INFO",
            message=(f"已触发训练命令：{start_command} (PID {process.pid})"),
        )
    )
    run = store.update_run_status(run.id, RunStatus.RUNNING, progress=0.05)
    return run


