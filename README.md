# LLM Training Management API

This project provides a FastAPI-based service to manage large language model training projects and runs. It supports the following core capabilities:

1. **Create Training Projects** – Define project metadata, such as name, objectives, task type, base model, and owner (requirement 5.2.1).
2. **Query Project Details** – Retrieve a project's status, run history, and configuration (requirement 5.2.2).
3. **Launch Training Runs** – Start training jobs for a project with configurable model, dataset, hyperparameters, and resource allocations (requirement 5.2.3).
4. **Monitor Run Status** – Inspect the current state of an individual run, including metrics and progress (requirement 5.2.4).
5. **Cancel Runs** – Safely stop active runs and persist checkpoints (requirement 5.2.5).
6. **Fetch Logs** – Retrieve training logs with pagination and optional time filters (requirement 5.2.6).
7. **List Artifacts** – Enumerate run outputs such as checkpoints, TensorBoard logs, and configuration files (requirement 5.2.7).
8. **Resume Training** – Continue training from a stored checkpoint for fault recovery or extended training (requirement 5.2.8).
9. **Tag Checkpoints** – Mark checkpoints as candidate bases or release versions (requirement 5.2.9).

## Getting Started

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the development server:

```bash
uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> to explore the interactive API documentation.
