"""FastAPI router that exposes endpoints for training jobs."""
from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models import JobStatus, TrainingJob
from app.services.jobs import JobStore

router = APIRouter(prefix="/jobs", tags=["jobs"])
store = JobStore()


class HyperParameters(BaseModel):
    learning_rate: float = Field(..., gt=0, description="Optimizer learning rate")
    epochs: int = Field(..., ge=1, description="Number of training epochs")


class CreateJobRequest(BaseModel):
    job_id: str = Field(..., description="Unique identifier for the training job")
    model_name: str = Field(..., description="Name of the target model")
    dataset: str = Field(..., description="Dataset used for training")
    hyperparameters: Dict[str, float] = Field(..., description="Training hyperparameters")


class JobResponse(BaseModel):
    id: str
    model_name: str
    dataset: str
    hyperparameters: Dict[str, float]
    status: JobStatus
    created_at: str
    updated_at: str
    error_message: str | None

    @classmethod
    def from_model(cls, job: TrainingJob) -> "JobResponse":
        return cls(
            id=job.id,
            model_name=job.model_name,
            dataset=job.dataset,
            hyperparameters=job.hyperparameters,
            status=job.status,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            error_message=job.error_message,
        )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: CreateJobRequest) -> JobResponse:
    job = TrainingJob(
        id=payload.job_id,
        model_name=payload.model_name,
        dataset=payload.dataset,
        hyperparameters=payload.hyperparameters,
    )
    try:
        store.create(job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return JobResponse.from_model(job)


@router.get("", response_model=List[JobResponse])
def list_jobs() -> List[JobResponse]:
    return [JobResponse.from_model(job) for job in store.all()]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.from_model(job)


class UpdateStatusRequest(BaseModel):
    status: JobStatus
    error_message: str | None = None


@router.patch("/{job_id}/status", response_model=JobResponse)
def update_status(job_id: str, payload: UpdateStatusRequest) -> JobResponse:
    try:
        job = store.update_status(job_id, payload.status, error_message=payload.error_message)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc
    return JobResponse.from_model(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str) -> None:
    try:
        store.delete(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

