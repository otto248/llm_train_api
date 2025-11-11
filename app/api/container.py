"""Container helper endpoints."""

from __future__ import annotations

import logging
import shlex
from pathlib import Path as PathlibPath

from fastapi import APIRouter, Body, HTTPException

from ..config import CONTAINER_FILE_CONTENT, CONTAINER_FILE_TARGET_DIR, LOCAL_DOCKER_CONTAINER_NAME
from ..models import ContainerFileRequest, ContainerFileResponse
from ..utils import run_container_command

router = APIRouter(prefix="/containers/mycontainer", tags=["containers"])
logger = logging.getLogger(__name__)


def _create_file_in_container(filename: str) -> str:
    """Validate the desired filename and create the file inside the container."""
    sanitized = PathlibPath(filename).name
    if sanitized != filename:
        raise HTTPException(status_code=400, detail="文件名非法，仅允许提供文件名。")
    if sanitized in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="文件名不能为空或特殊目录。")
    target_path = f"{CONTAINER_FILE_TARGET_DIR}/{sanitized}"
    shell_command = (
        f"mkdir -p {CONTAINER_FILE_TARGET_DIR} && "
        f"printf %s {shlex.quote(CONTAINER_FILE_CONTENT)} > {shlex.quote(target_path)}"
    )
    try:
        run_container_command(
            LOCAL_DOCKER_CONTAINER_NAME,
            shell_command,
            log=logger,
        )
    except RuntimeError as exc:  # pragma: no cover - depends on runtime environment
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return target_path


@router.post("/files", response_model=ContainerFileResponse, status_code=201)
def create_container_file(
    payload: ContainerFileRequest = Body(ContainerFileRequest()),
) -> ContainerFileResponse:
    """在指定容器的 /mnt/disk 目录下创建文件并写入固定内容。"""

    file_path = _create_file_in_container(payload.filename)
    return ContainerFileResponse(path=file_path, content=CONTAINER_FILE_CONTENT)
