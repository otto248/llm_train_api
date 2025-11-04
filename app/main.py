from __future__ import annotations

from copy import deepcopy
from datetime import datetime


from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import engine, get_session
from .models import CheckpointTag, Experiment, ExperimentEvent, IdempotencyKey, Run, Base
from .schemas import (
    CheckpointMarkRequest,
    CheckpointMarkResponse,
    ExperimentCreate,
    ExperimentDetailResponse,
    ExperimentResponse,
    RunCancelResponse,
    RunCreate,
    RunResponse,
    RunResumeRequest,
    RunResumeResponse,
    RunStatusResponse,
    RunSummary,
)
from .utils import compute_payload_hash, generate_experiment_id, generate_run_id

app = FastAPI(title="LLM Training API", version="1.4")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def _experiment_to_response(experiment: Experiment) -> ExperimentResponse:
    return ExperimentResponse(
        experiment_id=experiment.id,
        status=experiment.status,
        name=experiment.name,
        task_type=experiment.task_type,
        version=experiment.version,
        owner=experiment.owner,
        created_at=experiment.created_at,
        dashboard_url=f"/v1/experiments/{experiment.id}",
    )


@app.post("/v1/experiments", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: ExperimentCreate,
    request: Request,
    session: Session = Depends(get_session),
) -> ExperimentResponse:
    idem_key = request.headers.get("Idempotency-Key")
    payload_hash = compute_payload_hash(payload.model_dump())

    if idem_key:
        existing_key = session.scalar(select(IdempotencyKey).where(IdempotencyKey.key == idem_key))
        if existing_key:
            if existing_key.request_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key conflict with different payload",
                )
            experiment = session.get(Experiment, existing_key.experiment_id)
            if experiment is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
            return _experiment_to_response(experiment)

    experiment = Experiment(
        id=generate_experiment_id(),
        name=payload.name,
        task_type=payload.task_type,
        goal=payload.goal,
        version=payload.version,
        base_model=payload.base_model,
        owner=payload.owner,
        param_config=payload.param_config,
        tags=payload.tags,
        status="CREATED",
        created_at=datetime.utcnow(),
    )
    session.add(experiment)
    session.add(ExperimentEvent(experiment_id=experiment.id, event="CREATED"))
    session.flush()

    if idem_key:
        session.add(
            IdempotencyKey(
                key=idem_key,
                request_hash=payload_hash,
                experiment_id=experiment.id,
            )
        )

    session.commit()
    session.refresh(experiment)
    return _experiment_to_response(experiment)


@app.get("/v1/experiments/{experiment_id}/detail", response_model=ExperimentDetailResponse)
def get_experiment_detail(
    experiment_id: str,
    session: Session = Depends(get_session),
) -> ExperimentDetailResponse:
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    runs = [RunSummary.model_validate(run, from_attributes=True) for run in experiment.runs]
    history = [
        {
            "event": event.event,
            "detail": event.detail,
            "created_at": event.created_at,
        }
        for event in experiment.events
    ]

    response = ExperimentDetailResponse(
        experiment_id=experiment.id,
        status=experiment.status,
        name=experiment.name,
        task_type=experiment.task_type,
        version=experiment.version,
        owner=experiment.owner,
        goal=experiment.goal,
        base_model=experiment.base_model,
        param_config=experiment.param_config,
        tags=experiment.tags,
        created_at=experiment.created_at,
        runs=runs,
        history=history,
    )
    return response


@app.post("/v1/experiments/{experiment_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    experiment_id: str,
    payload: RunCreate,
    session: Session = Depends(get_session),
) -> RunResponse:
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    run = Run(
        id=generate_run_id(),
        experiment_id=experiment_id,
        status="RUNNING",
        model_name=payload.model,
        dataset=payload.dataset,
        hyperparams=payload.hyperparams,
        resources=payload.resources,
        notes=payload.notes,
        progress=0.0,
        latest_metrics=[],
        started_at=datetime.utcnow(),
    )
    session.add(run)
    session.add(
        ExperimentEvent(
            experiment_id=experiment_id,
            event="RUN_STARTED",
            detail=f"Run {run.id} started",
        )
    )

    experiment.status = "RUNNING"

    session.commit()
    session.refresh(run)

    return RunResponse(
        run_id=run.id,
        experiment_id=run.experiment_id,
        status=run.status,
        started_at=run.started_at,
    )


@app.get("/v1/experiments/{experiment_id}/runs/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(
    experiment_id: str,
    run_id: str,
    session: Session = Depends(get_session),
) -> RunStatusResponse:
    run = session.get(Run, run_id)
    if run is None or run.experiment_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return RunStatusResponse(
        run_id=run.id,
        status=run.status,
        progress=run.progress,
        latest_metrics=run.latest_metrics or [],
    )


@app.post("/v1/experiments/{experiment_id}/runs/{run_id}/cancel", response_model=RunCancelResponse)
def cancel_run(
    experiment_id: str,
    run_id: str,
    session: Session = Depends(get_session),
) -> RunCancelResponse:
    run = session.get(Run, run_id)
    if run is None or run.experiment_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if run.status == "CANCELED":
        checkpoint_path = run.checkpoint_path or _build_checkpoint_path(run)
        return RunCancelResponse(run_id=run.id, status=run.status, checkpoint_path=checkpoint_path)

    run.status = "CANCELED"
    run.finished_at = datetime.utcnow()
    if not run.checkpoint_path:
        run.checkpoint_path = _build_checkpoint_path(run)

    session.add(
        ExperimentEvent(
            experiment_id=experiment_id,
            event="RUN_CANCELED",
            detail=f"Run {run.id} canceled",
        )
    )

    session.commit()
    session.refresh(run)
    return RunCancelResponse(run_id=run.id, status=run.status, checkpoint_path=run.checkpoint_path)


@app.post("/v1/experiments/{experiment_id}/runs/{run_id}/resume", response_model=RunResumeResponse, status_code=status.HTTP_201_CREATED)
def resume_run(
    experiment_id: str,
    run_id: str,
    payload: RunResumeRequest,
    session: Session = Depends(get_session),
) -> RunResumeResponse:
    parent_run = session.get(Run, run_id)
    if parent_run is None or parent_run.experiment_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    hyperparams = deepcopy(parent_run.hyperparams or {})
    hyperparams.update(payload.override_hyperparams)

    new_run = Run(
        id=generate_run_id(),
        experiment_id=experiment_id,
        status="RUNNING",
        model_name=parent_run.model_name,
        dataset=parent_run.dataset,
        hyperparams=hyperparams,
        resources=parent_run.resources,
        notes=payload.notes,
        progress=0.0,
        latest_metrics=[],
        started_at=datetime.utcnow(),
        parent_run_id=parent_run.id,
        from_checkpoint=payload.ckpt_path,
    )
    session.add(new_run)
    session.add(
        ExperimentEvent(
            experiment_id=experiment_id,
            event="RUN_RESUMED",
            detail=f"Run {new_run.id} resumed from {payload.ckpt_path}",
        )
    )

    session.commit()
    session.refresh(new_run)

    return RunResumeResponse(
        new_run_id=new_run.id,
        status=new_run.status,
        parent_run_id=parent_run.id,
        from_checkpoint=payload.ckpt_path,
    )


@app.post("/v1/experiments/{experiment_id}/checkpoints/mark", response_model=CheckpointMarkResponse)
def mark_checkpoint(
    experiment_id: str,
    payload: CheckpointMarkRequest,
    session: Session = Depends(get_session),
) -> CheckpointMarkResponse:
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    run = session.get(Run, payload.run_id)
    if run is None or run.experiment_id != experiment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    is_candidate_base = payload.tag_type.lower() == "candidate_base"

    checkpoint_tag = CheckpointTag(
        experiment_id=experiment_id,
        run_id=run.id,
        ckpt_path=payload.ckpt_path,
        tag_type=payload.tag_type,
        is_candidate_base=is_candidate_base,
        release_tag=payload.release_tag,
        metrics=payload.metrics,
    )
    session.add(checkpoint_tag)

    session.add(
        ExperimentEvent(
            experiment_id=experiment_id,
            event="CHECKPOINT_MARKED",
            detail=f"Checkpoint {payload.ckpt_path} tagged as {payload.tag_type}",
        )
    )

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CheckpointMarkResponse(
        experiment_id=experiment_id,
        run_id=run.id,
        ckpt_path=payload.ckpt_path,
        is_candidate_base=is_candidate_base,
        release_tag=payload.release_tag,
    )


def _build_checkpoint_path(run: Run) -> str:
    return f"/ckpts/{run.experiment_id}/{run.id}/latest.pt"
