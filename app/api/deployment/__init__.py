"""Model deployment management endpoints."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DEFAULT_HEALTH_PATH = "/health"
HTTP_CHECK_TIMEOUT = 2.0
PROCESS_TERMINATE_TIMEOUT = 10.0
PORT_RANGE = (8000, 8999)
VLLM_CMD_TEMPLATE = os.environ.get(
    "VLLM_CMD_TEMPLATE",
    "vllm --model {model_path} --http-port {port} --device-ids {gpu_id} {extra_args}",
)
LOG_DIR = os.environ.get("DEPLOY_LOG_DIR", "./deploy_logs")
os.makedirs(LOG_DIR, exist_ok=True)

router = APIRouter(prefix="/deployments", tags=["deployments"])

_store_lock = Lock()
_deployments: Dict[str, Dict[str, Any]] = {}

try:  # pragma: no cover - optional dependency
    import pynvml  # type: ignore

    PYNVML_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency may be unavailable
    PYNVML_AVAILABLE = False


class CreateDeploymentRequest(BaseModel):
    """Request payload for creating a new model deployment."""

    model_path: str
    model_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extra_args: str = Field(
        default="",
        description="传给 vllm 的额外参数",
    )
    preferred_gpu: Optional[int] = None
    health_path: str = DEFAULT_HEALTH_PATH


class DeploymentInfo(BaseModel):
    """Response model describing a deployment."""

    deployment_id: str
    model_path: str
    model_version: Optional[str]
    tags: List[str]
    gpu_id: Optional[int]
    port: int
    pid: Optional[int]
    status: str
    started_at: Optional[float]
    stopped_at: Optional[float]
    health_ok: Optional[bool]
    vllm_cmd: Optional[str]
    log_file: Optional[str]
    health_path: Optional[str]


class DeploymentRemoved(BaseModel):
    """Response returned when a deployment is removed."""

    detail: str
    deployment_id: str


def _get_gpu_free_memory() -> List[tuple[int, int]]:
    """Return a list of GPUs and their free memory in bytes."""

    results: List[tuple[int, int]] = []
    if PYNVML_AVAILABLE:
        try:  # pragma: no cover - depends on GPU hardware
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            for index in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                results.append((index, int(memory_info.free)))
            pynvml.nvmlShutdown()
            return results
        except Exception:
            results.clear()
    try:  # pragma: no cover - depends on GPU hardware
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
        for line in output.strip().splitlines():
            if not line:
                continue
            index_str, memory_str = [segment.strip() for segment in line.split(",", maxsplit=1)]
            results.append((int(index_str), int(memory_str) * 1024 * 1024))
    except Exception:
        pass
    return results


def _pick_gpu(preferred: Optional[int] = None) -> Optional[int]:
    """Pick a GPU, preferring the requested device when available."""

    gpus = _get_gpu_free_memory()
    if not gpus:
        return None
    if preferred is not None:
        for gpu_id, _ in gpus:
            if gpu_id == preferred:
                return gpu_id
    gpu_id, _ = max(gpus, key=lambda item: item[1])
    return gpu_id


def _is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if the provided port is available for binding."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def _find_free_port(low: int = PORT_RANGE[0], high: int = PORT_RANGE[1]) -> int:
    """Locate an available TCP port."""

    for port in range(low, high + 1):
        if _is_port_free(port):
            return port
    raise RuntimeError("no free port available")


def _start_vllm_process(
    *,
    model_path: str,
    port: int,
    gpu_id: Optional[int],
    extra_args: str,
    log_file_path: str,
) -> subprocess.Popen[Any]:
    """Launch the vLLM process using the configured command template."""

    environment = os.environ.copy()
    if gpu_id is None:
        environment.pop("CUDA_VISIBLE_DEVICES", None)
    else:
        environment["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    command = VLLM_CMD_TEMPLATE.format(
        model_path=model_path,
        port=port,
        gpu_id=gpu_id if gpu_id is not None else "",
        extra_args=extra_args or "",
    )
    log_file = open(log_file_path, "a", encoding="utf-8")
    return subprocess.Popen(  # noqa: S603, S607 - user provided command template
        command,
        shell=True,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=environment,
        preexec_fn=os.setsid,
    )


def _check_http_health(port: int, path: str = DEFAULT_HEALTH_PATH) -> bool:
    """Check the HTTP health endpoint exposed by the deployment."""

    base_url = f"http://127.0.0.1:{port}"
    try:
        response = requests.get(f"{base_url}{path}", timeout=HTTP_CHECK_TIMEOUT)
        if response.status_code == 200:
            return True
    except Exception:
        pass
    try:
        response = requests.get(f"{base_url}/", timeout=HTTP_CHECK_TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


@router.post("", response_model=DeploymentInfo, status_code=201)
def create_deployment(
    payload: CreateDeploymentRequest,
    background_tasks: BackgroundTasks,
) -> DeploymentInfo:
    """Create a new deployment and start the associated vLLM process."""

    gpu_id = _pick_gpu(payload.preferred_gpu)
    try:
        port = _find_free_port()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    deployment_id = str(uuid.uuid4())
    started_at = time.time()
    log_file = os.path.join(LOG_DIR, f"{deployment_id}.log")
    vllm_cmd = VLLM_CMD_TEMPLATE.format(
        model_path=payload.model_path,
        port=port,
        gpu_id=gpu_id if gpu_id is not None else "",
        extra_args=payload.extra_args or "",
    )

    try:
        process = _start_vllm_process(
            model_path=payload.model_path,
            port=port,
            gpu_id=gpu_id,
            extra_args=payload.extra_args,
            log_file_path=log_file,
        )
        pid = process.pid
    except Exception as exc:
        with _store_lock:
            _deployments[deployment_id] = {
                "deployment_id": deployment_id,
                "model_path": payload.model_path,
                "model_version": payload.model_version,
                "tags": payload.tags,
                "gpu_id": gpu_id,
                "port": port,
                "pid": None,
                "status": "failed",
                "started_at": started_at,
                "stopped_at": time.time(),
                "health_ok": False,
                "vllm_cmd": vllm_cmd,
                "log_file": log_file,
                "health_path": payload.health_path or DEFAULT_HEALTH_PATH,
            }
        raise HTTPException(status_code=500, detail=f"failed to start process: {exc}") from exc

    with _store_lock:
        _deployments[deployment_id] = {
            "deployment_id": deployment_id,
            "model_path": payload.model_path,
            "model_version": payload.model_version,
            "tags": payload.tags,
            "gpu_id": gpu_id,
            "port": port,
            "pid": pid,
            "status": "starting",
            "started_at": started_at,
            "stopped_at": None,
            "health_ok": False,
            "vllm_cmd": vllm_cmd,
            "log_file": log_file,
            "health_path": payload.health_path or DEFAULT_HEALTH_PATH,
        }

    def _background_health_check(
        deployment_identifier: str,
        process_id: int,
        port_number: int,
        health_path: str,
    ) -> None:
        """在后台轮询部署健康状态并更新存储。"""

        time.sleep(1.0)
        try:
            os.kill(process_id, 0)
        except Exception:
            with _store_lock:
                record = _deployments.get(deployment_identifier)
                if record:
                    record["status"] = "stopped"
                    record["health_ok"] = False
                    record["stopped_at"] = time.time()
            return
        success = False
        for _ in range(12):
            if _check_http_health(port_number, health_path):
                success = True
                break
            time.sleep(0.5)
        with _store_lock:
            record = _deployments.get(deployment_identifier)
            if record:
                record["status"] = "running"
                record["health_ok"] = success

    background_tasks.add_task(
        _background_health_check,
        deployment_id,
        pid,
        port,
        payload.health_path or DEFAULT_HEALTH_PATH,
    )
    return DeploymentInfo(**_deployments[deployment_id])


@router.get("/{deployment_id}", response_model=DeploymentInfo)
def get_deployment(deployment_id: str) -> DeploymentInfo:
    """Return metadata about a specific deployment."""

    with _store_lock:
        record = _deployments.get(deployment_id)
        if not record:
            raise HTTPException(status_code=404, detail="deployment not found")
        pid = record.get("pid")
    if pid:
        alive = True
        try:
            os.kill(pid, 0)
        except Exception:
            alive = False
        with _store_lock:
            record["status"] = "running" if alive else "stopped"
            if alive:
                record["health_ok"] = _check_http_health(
                    record["port"],
                    record.get("health_path", DEFAULT_HEALTH_PATH),
                )
            else:
                record["health_ok"] = False
    return DeploymentInfo(**record)


@router.delete("/{deployment_id}", response_model=DeploymentRemoved)
def delete_deployment(
    deployment_id: str,
    force: bool = Query(False, description="是否在进程无法正常退出时强制杀掉"),
) -> DeploymentRemoved:
    """Stop and remove a deployment."""

    with _store_lock:
        record = _deployments.get(deployment_id)
        if not record:
            raise HTTPException(status_code=404, detail="deployment not found")
        pid = record.get("pid")
        record["status"] = "stopping"

    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        start = time.time()
        stopped = False
        while time.time() - start < PROCESS_TERMINATE_TIMEOUT:
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except Exception:
                stopped = True
                break
        if not stopped:
            if force:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
            else:
                with _store_lock:
                    _deployments[deployment_id]["status"] = "stopping"
                raise HTTPException(
                    status_code=409,
                    detail="process did not stop within timeout; retry with force=true",
                )

    with _store_lock:
        record = _deployments.pop(deployment_id, None)
        if record:
            record["status"] = "stopped"
            record["stopped_at"] = time.time()

    return DeploymentRemoved(detail="deployment removed", deployment_id=deployment_id)


@router.get("", response_model=List[DeploymentInfo])
def list_deployments(
    model: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
) -> List[DeploymentInfo]:
    """List deployments with optional filtering."""

    response: List[DeploymentInfo] = []
    with _store_lock:
        for record in _deployments.values():
            pid = record.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)
                    record["status"] = "running"
                    record["health_ok"] = _check_http_health(
                        record["port"],
                        record.get("health_path", DEFAULT_HEALTH_PATH),
                    )
                except Exception:
                    record["status"] = "stopped"
                    record["health_ok"] = False
        for record in _deployments.values():
            if model and model not in (record.get("model_path") or ""):
                continue
            if tag and tag not in (record.get("tags") or []):
                continue
            if status and (record.get("status") or "").lower() != status.lower():
                continue
            response.append(DeploymentInfo(**record))
    return response


def register_routes(app: FastAPI) -> None:
    """Register deployment management endpoints on the provided application."""

    app.include_router(router)
