"""Tests for the training job router."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def get_client() -> TestClient:
    return TestClient(create_app())


def test_create_and_retrieve_job() -> None:
    client = get_client()
    payload = {
        "job_id": "job-1",
        "model_name": "gpt-mini",
        "dataset": "datasets/corpus.jsonl",
        "hyperparameters": {"learning_rate": 0.001, "epochs": 3},
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "job-1"
    assert data["status"] == "queued"

    get_response = client.get("/jobs/job-1")
    assert get_response.status_code == 200
    retrieved = get_response.json()
    assert retrieved["model_name"] == "gpt-mini"


def test_update_status_and_list_jobs() -> None:
    client = get_client()
    payload = {
        "job_id": "job-2",
        "model_name": "gpt-mini",
        "dataset": "datasets/corpus.jsonl",
        "hyperparameters": {"learning_rate": 0.001, "epochs": 3},
    }
    client.post("/jobs", json=payload)

    list_response = client.get("/jobs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.patch(
        "/jobs/job-2/status",
        json={"status": "running"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "running"


def test_delete_job() -> None:
    client = get_client()
    payload = {
        "job_id": "job-3",
        "model_name": "gpt-mini",
        "dataset": "datasets/corpus.jsonl",
        "hyperparameters": {"learning_rate": 0.001, "epochs": 3},
    }
    client.post("/jobs", json=payload)

    delete_response = client.delete("/jobs/job-3")
    assert delete_response.status_code == 204

    missing_response = client.get("/jobs/job-3")
    assert missing_response.status_code == 404

