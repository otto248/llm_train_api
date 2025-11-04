from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _to_epoch(value: Optional[datetime]) -> Optional[int]:
    if value is None:
        return None
    return int(value.timestamp())


class ExperimentCreate(BaseModel):
    name: str
    task_type: str
    goal: Optional[str] = None
    version: Optional[str] = None
    base_model: Optional[str] = None
    owner: Optional[str] = None
    param_config: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class ExperimentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    experiment_id: str = Field(alias="id")
    status: str
    name: str
    task_type: str
    version: Optional[str] = None
    owner: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime) -> int:
        return _to_epoch(value) or 0


class ExperimentResponse(ExperimentSummary):
    dashboard_url: str


class ExperimentDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: str = Field(alias="id")
    status: str
    name: str
    task_type: str
    version: Optional[str] = None
    owner: Optional[str] = None
    goal: Optional[str] = None
    base_model: Optional[str] = None
    param_config: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    runs: List["RunSummary"]
    history: List["ExperimentEventSchema"]

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime) -> int:
        return _to_epoch(value) or 0


class ExperimentEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str
    detail: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime) -> int:
        return _to_epoch(value) or 0


class RunCreate(BaseModel):
    model: str
    dataset: Dict[str, Any]
    hyperparams: Dict[str, Any]
    resources: Dict[str, Any]
    notes: Optional[str] = None


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    run_id: str = Field(alias="id")
    status: str


class RunResponse(RunSummary):
    experiment_id: str
    status: str
    started_at: datetime

    @field_serializer("started_at", when_used="json")
    def serialize_started_at(cls, value: datetime) -> int:
        return _to_epoch(value) or 0


class RunStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    run_id: str = Field(alias="id")
    status: str
    progress: float
    latest_metrics: List[Dict[str, Any]]


class RunCancelResponse(BaseModel):
    run_id: str
    status: str
    checkpoint_path: str


class RunResumeRequest(BaseModel):
    ckpt_path: str
    override_hyperparams: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class RunResumeResponse(BaseModel):
    new_run_id: str
    status: str
    parent_run_id: str
    from_checkpoint: str


class CheckpointMarkRequest(BaseModel):
    run_id: str
    ckpt_path: str
    tag_type: str
    release_tag: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class CheckpointMarkResponse(BaseModel):
    experiment_id: str
    run_id: str
    ckpt_path: str
    is_candidate_base: bool
    release_tag: Optional[str] = None

ExperimentDetailResponse.model_rebuild()
