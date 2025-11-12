from __future__ import annotations

from app.api.v1.projects.schemas import ProjectCreate, RunStatus
from app.api.v1.projects.service import TrainingService


def create_payload() -> ProjectCreate:
    return ProjectCreate(
        name="qwen-pretrain",
        description="Qwen 预训练任务",
        owner="alice",
        tags=["nlp", "pretrain"],
        dataset_name="datasets/qwen_mix.parquet",
        training_yaml_name="configs/qwen_pretrain.yaml",
    )


def test_create_project(service: TrainingService) -> None:
    payload = create_payload()
    project = service.create_project(payload)
    assert project.name == payload.name
    assert project.runs == []


def test_list_projects(service: TrainingService) -> None:
    payload = create_payload()
    service.create_project(payload)
    projects = service.list_projects()
    assert len(projects) == 1
    assert projects[0].name == payload.name


def test_create_run(service: TrainingService) -> None:
    payload = create_payload()
    project = service.create_project(payload)
    run = service.create_run(project.id)
    assert run.status == RunStatus.RUNNING
    assert run.progress == service.settings.default_run_progress
    messages = [entry.message for entry in run.logs]
    assert any("模拟触发训练命令" in message for message in messages)
