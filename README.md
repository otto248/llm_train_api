# LLM Training Management API

This repository provides a FastAPI-based service for managing large language model (LLM) training projects and their lifecycle runs. The service covers the full workflow from defining a training project to launching, monitoring, cancelling, resuming runs, and managing the produced artifacts.

## Table of Contents
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Running the API](#running-the-api)
- [API Reference](#api-reference)
  - [Create a Project](#create-a-project)
  - [List Projects](#list-projects)
  - [Get Project Details](#get-project-details)
  - [Create a Run](#create-a-run)
  - [Get Run Details](#get-run-details)
  - [Cancel a Run](#cancel-a-run)
  - [Fetch Run Logs](#fetch-run-logs)
  - [List Run Artifacts](#list-run-artifacts)
  - [Resume a Run](#resume-a-run)
  - [Tag an Artifact](#tag-an-artifact)
- [In-Memory Storage Behaviour](#in-memory-storage-behaviour)
- [Development Tips](#development-tips)

## Features
- Define projects with metadata such as name, description, goals, task type, base model, and owner (requirement 5.2.1).
- Inspect project state, run counts, configuration defaults, version history, and associated runs (requirement 5.2.2).
- Launch new training runs with model, dataset, hyper-parameters, and resource configuration (requirement 5.2.3).
- Monitor training progress including status, metrics, timestamps, and GPU usage (requirement 5.2.4).
- Cancel active runs while persisting the latest checkpoint (requirement 5.2.5).
- Retrieve paginated logs with optional time filters (requirement 5.2.6).
- List artifacts (checkpoints, TensorBoard logs, evaluation results, configs) (requirement 5.2.7).
- Resume training from a chosen checkpoint (requirement 5.2.8).
- Tag checkpoints as candidate base models or release versions (requirement 5.2.9).

## Architecture Overview
The FastAPI service is organised into three main modules:

| Module | Description |
| --- | --- |
| `app/main.py` | Declares the FastAPI application and all REST endpoints. |
| `app/models.py` | Defines Pydantic request/response models used for validation and serialization. |
| `app/storage.py` | Implements an in-memory storage layer that simulates projects, runs, logs, metrics, and artifacts. |

> **Note:** The storage layer keeps data only for the duration of the process. Restarting the server clears all state.

## Getting Started
Install dependencies (Python 3.10+ recommended):

```bash
pip install -r requirements.txt
```

Optionally run a quick syntax check:

```bash
python -m compileall app
```

## Running the API
Start the development server:

```bash
uvicorn app.main:app --reload
```

The OpenAPI/Swagger UI is available at <http://localhost:8000/docs>. Postman or any HTTP client can also be used to interact with the API.

## API Reference
All endpoints return JSON responses and use standard HTTP status codes. Unless specified, request bodies must be sent as JSON.

### Create a Project
- **Method & Path:** `POST /projects`
- **Description:** Create a new training project and persist its metadata (requirement 5.2.1).
- **Request Body:**
  ```json
  {
    "name": "Text Summarization",
    "description": "Summarize scientific articles",
    "objective": "Reduce reading time",
    "task_type": "summarization",
    "base_model": "llama-2-13b",
    "owner": "alice",
    "tags": ["research", "phase-1"],
    "default_hyperparameters": {
      "learning_rate": 3e-5,
      "batch_size": 16
    }
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "id": "proj_xxx",
    "name": "Text Summarization",
    "status": "draft",
    "objective": "Reduce reading time",
    "task_type": "summarization",
    "base_model": "llama-2-13b",
    "owner": "alice",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "tags": ["research", "phase-1"],
    "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
    "runs": []
  }
  ```

### List Projects
- **Method & Path:** `GET /projects`
- **Description:** Retrieve a summary list of all projects.
- **Response:** `200 OK`
  ```json
  [
    {
      "id": "proj_xxx",
      "name": "Text Summarization",
      "status": "draft",
      "owner": "alice",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
  ```

### Get Project Details
- **Method & Path:** `GET /projects/{project_id}`
- **Description:** Get detailed project information including associated runs (requirement 5.2.2).
- **Response:** `200 OK`
  ```json
  {
    "id": "proj_xxx",
    "name": "Text Summarization",
    "status": "active",
    "objective": "Reduce reading time",
    "task_type": "summarization",
    "base_model": "llama-2-13b",
    "owner": "alice",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-02T09:30:00Z",
    "tags": ["research", "phase-1"],
    "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
    "runs": [
      {
        "id": "run_001",
        "project_id": "proj_xxx",
        "status": "running",
        "started_at": "2024-01-02T09:30:00Z",
        "progress": 0.35
      }
    ]
  }
  ```

### Create a Run
- **Method & Path:** `POST /projects/{project_id}/runs`
- **Description:** Launch a training run under the given project (requirement 5.2.3).
- **Request Body:**
  ```json
  {
    "name": "run-001",
    "description": "Fine-tune on curated dataset",
    "dataset": "s3://datasets/articles.jsonl",
    "model_parameters": {
      "max_steps": 10000,
      "eval_interval": 500
    },
    "hyperparameters": {
      "learning_rate": 2e-5,
      "batch_size": 32,
      "gradient_accumulation": 2
    },
    "compute": {
      "node_count": 2,
      "gpus_per_node": 8,
      "gpu_type": "A100-80GB"
    }
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "id": "run_001",
    "project_id": "proj_xxx",
    "name": "run-001",
    "status": "running",
    "progress": 0.05,
    "metrics": {
      "loss": 2.1,
      "accuracy": 0.0,
      "throughput_tokens_per_s": 0.0,
      "gpu_utilization": 0.42
    },
    "started_at": "2024-01-02T09:30:00Z",
    "updated_at": "2024-01-02T09:30:00Z",
    "artifacts": []
  }
  ```

### Get Run Details
- **Method & Path:** `GET /projects/{project_id}/runs/{run_id}`
- **Description:** Inspect the current status and metrics for a run (requirement 5.2.4).
- **Response:** `200 OK`
  ```json
  {
    "id": "run_001",
    "project_id": "proj_xxx",
    "name": "run-001",
    "status": "running",
    "progress": 0.42,
    "metrics": {
      "loss": 1.4,
      "accuracy": 0.68,
      "throughput_tokens_per_s": 850.0,
      "gpu_utilization": 0.77
    },
    "started_at": "2024-01-02T09:30:00Z",
    "updated_at": "2024-01-02T12:00:00Z",
    "completed_at": null,
    "artifacts": [
      {
        "id": "ckpt_001",
        "name": "Checkpoint @ step 2000",
        "type": "checkpoint",
        "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
        "created_at": "2024-01-02T11:45:00Z",
        "tags": []
      }
    ]
  }
  ```

### Cancel a Run
- **Method & Path:** `POST /projects/{project_id}/runs/{run_id}/cancel`
- **Description:** Cancel an active run and capture a final checkpoint (requirement 5.2.5).
- **Response:** `200 OK`
  ```json
  {
    "id": "run_001",
    "status": "cancelled",
    "completed_at": "2024-01-02T12:05:00Z",
    "artifacts": [
      {
        "id": "ckpt_cancel",
        "name": "Checkpoint before cancel",
        "type": "checkpoint",
        "path": "s3://artifacts/proj_xxx/run_001/ckpt_cancel.pt",
        "created_at": "2024-01-02T12:05:00Z",
        "tags": []
      }
    ]
  }
  ```

### Fetch Run Logs
- **Method & Path:** `GET /projects/{project_id}/runs/{run_id}/logs`
- **Description:** Retrieve logs for a run with pagination and optional time range filters (requirement 5.2.6).
- **Query Parameters:**
  | Name | Type | Default | Description |
  | --- | --- | --- | --- |
  | `page` | integer | `1` | Page number (1-indexed). |
  | `page_size` | integer | `50` | Number of log lines per page (1–500). |
  | `start_time` | ISO 8601 datetime | `null` | Filter to logs at or after this timestamp. |
  | `end_time` | ISO 8601 datetime | `null` | Filter to logs before this timestamp. |
- **Response:** `200 OK`
  ```json
  {
    "page": 1,
    "page_size": 50,
    "total": 120,
    "items": [
      {
        "timestamp": "2024-01-02T10:00:00Z",
        "level": "INFO",
        "message": "Step 500 - loss=1.86 lr=2e-5"
      }
    ]
  }
  ```

### List Run Artifacts
- **Method & Path:** `GET /projects/{project_id}/runs/{run_id}/artifacts`
- **Description:** List checkpoints and other outputs created by the run (requirement 5.2.7).
- **Response:** `200 OK`
  ```json
  {
    "items": [
      {
        "id": "ckpt_001",
        "name": "Checkpoint @ step 2000",
        "type": "checkpoint",
        "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
        "created_at": "2024-01-02T11:45:00Z",
        "size_bytes": 123456789,
        "tags": []
      }
    ]
  }
  ```

### Resume a Run
- **Method & Path:** `POST /projects/{project_id}/runs/{run_id}/resume`
- **Description:** Resume or extend training from an existing checkpoint (requirement 5.2.8).
- **Query Parameters:**
  | Name | Type | Required | Description |
  | --- | --- | --- | --- |
  | `source_artifact_id` | string | Yes | ID of the checkpoint artifact to resume from. |
- **Request Body:** Same schema as [Create a Run](#create-a-run). Allows overriding hyperparameters for the resumed run.
- **Response:** `201 Created`
  ```json
  {
    "id": "run_002",
    "project_id": "proj_xxx",
    "name": "run-002",
    "status": "running",
    "resumed_from": "ckpt_001",
    "progress": 0.05,
    "started_at": "2024-01-03T08:00:00Z",
    "artifacts": []
  }
  ```

### Tag an Artifact
- **Method & Path:** `POST /projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/tag`
- **Description:** Mark a checkpoint as a candidate base model or publish it as a release (requirement 5.2.9).
- **Request Body:**
  ```json
  {
    "tag": "release",
    "notes": "Validated on hold-out set with BLEU 32.5"
  }
  ```
  Valid tags: `candidate`, `release`, `archived`.
- **Response:** `200 OK`
  ```json
  {
    "id": "ckpt_001",
    "name": "Checkpoint @ step 2000",
    "type": "checkpoint",
    "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
    "created_at": "2024-01-02T11:45:00Z",
    "tags": [
      {
        "value": "release",
        "notes": "Validated on hold-out set with BLEU 32.5",
        "applied_at": "2024-01-03T09:15:00Z"
      }
    ]
  }
  ```

## In-Memory Storage Behaviour
The demo storage layer is purposefully simple:
- IDs are generated with short prefixes (e.g., `proj_`, `run_`, `ckpt_`).
- Runs automatically receive simulated metrics, logs, and artifacts.
- Cancelling a run changes its status to `cancelled` and emits a final checkpoint artifact.
- Resuming a run clones the configuration of the original run while linking to the source checkpoint.

For production use, replace `app/storage.py` with integrations to your actual database, job scheduler, telemetry, and artifact systems.

## Development Tips
- Use the included Pydantic models in `app/models.py` as a contract for client/server communication.
- Extend `InMemoryStorage` or swap it out with persistent storage for real deployments.
- Add authentication, authorization, and multi-tenant isolation as needed for your environment.
- Consider adding background workers or Celery tasks for long-running training orchestration.
