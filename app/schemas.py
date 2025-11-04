from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, FieldSerializationInfo, field_serializer


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
    run_count: int = 0

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
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
    run_count: int
    runs: List["RunSummary"]
    history: List["ExperimentEventSchema"]

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
        return _to_epoch(value) or 0


class ExperimentEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event: str
    detail: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
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
    def serialize_started_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
        return _to_epoch(value) or 0


class RunStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    run_id: str = Field(alias="id")
    status: str
    progress: float
    latest_metrics: List[Dict[str, Any]]
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @field_serializer("started_at", when_used="json")
    def serialize_started_at(
        cls,
        value: Optional[datetime],
        info: FieldSerializationInfo,  # noqa: ARG002
    ) -> Optional[int]:
        return _to_epoch(value)

    @field_serializer("finished_at", when_used="json")
    def serialize_finished_at(
        cls,
        value: Optional[datetime],
        info: FieldSerializationInfo,  # noqa: ARG002
    ) -> Optional[int]:
        return _to_epoch(value)


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


class RunLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    level: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
        return _to_epoch(value) or 0


class RunLogResponse(BaseModel):
    run_id: str
    items: List[RunLogEntry]
    total: int
    limit: int
    offset: int


class RunArtifactSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_id: int = Field(alias="id")
    artifact_type: str
    path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(cls, value: datetime, info: FieldSerializationInfo) -> int:  # noqa: ARG002
        return _to_epoch(value) or 0


class RunArtifactListResponse(BaseModel):
    run_id: str
    items: List[RunArtifactSchema]


ExperimentDetailResponse.model_rebuild()
