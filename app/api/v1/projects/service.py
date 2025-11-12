from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from app.api.v1.projects.repository import ProjectRepository
from app.api.v1.projects.schemas import ProjectCreate, ProjectDetail, Project, RunDetail, RunStatus
from app.common.utils import ensure_subpath
from app.core.config import Settings

logger = logging.getLogger(__name__)


class TrainingService:
    def __init__(self, repository: ProjectRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def create_project(self, payload: ProjectCreate) -> ProjectDetail:
        project = self.repository.create_project(payload)
        return ProjectDetail.model_validate(project)

    def list_projects(self) -> list[Project]:
        return [Project.model_validate(project) for project in self.repository.list_projects()]

    def create_run(self, project_reference: str) -> RunDetail:
        project = self._get_project_by_reference(project_reference)
        self._ensure_project_assets(project)
        start_command = self._build_start_command(project)
        run = self.repository.create_run(project, start_command)
        run = self.repository.append_run_logs(
            run,
            [
                (
                    "INFO",
                    f"已确认训练资源数据集 {project.dataset_name}，配置 {project.training_yaml_name}",
                )
            ],
        )
        if self.settings.enable_process_launch:
            try:
                process = self._launch_training_process(start_command)
                run = self.repository.append_run_logs(
                    run,
                    [
                        (
                            "INFO",
                            f"已触发训练命令：{start_command} (PID {process.pid})",
                        )
                    ],
                )
            except RuntimeError as exc:
                run = self.repository.append_run_logs(run, [("ERROR", str(exc))])
                self.repository.update_run_status(run, RunStatus.FAILED)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        else:
            run = self.repository.append_run_logs(
                run,
                [("INFO", f"模拟触发训练命令：{start_command}")],
            )
        run = self.repository.update_run_status(
            run, RunStatus.RUNNING, progress=self.settings.default_run_progress
        )
        return RunDetail.model_validate(run)

    # Helpers
    def _get_project_by_reference(self, reference: str):
        project = self.repository.get_project_by_id(reference)
        if project is None:
            project = self.repository.get_project_by_name(reference)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    def _ensure_project_assets(self, project) -> None:
        base_dir = self.settings.host_training_dir
        if base_dir is None:
            return
        missing: list[str] = []
        dataset_path = ensure_subpath(Path(base_dir), project.dataset_name)
        if not dataset_path.exists():
            missing.append(f"数据集 {project.dataset_name}")
        yaml_path = ensure_subpath(Path(base_dir), project.training_yaml_name)
        if not yaml_path.exists():
            missing.append(f"训练配置 {project.training_yaml_name}")
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="以下项目资源尚未上传完成：" + "、".join(missing),
            )

    def _build_start_command(self, project) -> str:
        return f"bash run_train_full_sft.sh {project.training_yaml_name}"

    def _launch_training_process(self, start_command: str) -> subprocess.Popen[bytes]:
        host_dir = self.settings.host_training_dir
        container = self.settings.docker_container_name
        workdir = self.settings.docker_working_dir
        if not host_dir or not container or not workdir:
            raise RuntimeError("训练命令执行所需的环境变量未完整配置。")
        docker_command = (
            f"cd {host_dir} && "
            f"docker exec -i {container} "
            "env LANG=C.UTF-8 bash -lc "
            f"\"cd {workdir} && {start_command}\""
        )
        logger.info("Launching training command: %s", docker_command)
        try:
            process = subprocess.Popen(  # noqa: S603, S607
                ["bash", "-lc", docker_command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("无法执行训练命令，请检查服务器环境配置。") from exc
        return process
