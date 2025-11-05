# LLM 训练管理 API

基于 FastAPI 的轻量级服务，用于集中管理大模型训练项目并触发运行。核心逻辑围绕“项目配置”和“训练运行”两类资源展开，便于快速对接现有训练脚本或调度系统。

## 核心功能
- **项目管理**：保存项目的名称、负责人、关联数据集和训练配置等关键信息。
- **项目列表**：快速浏览所有项目及其当前状态，支持按 ID 或名称检索。
- **触发训练**：为任意项目创建新的训练运行，自动生成启动命令并返回运行详情、工件和日志摘要。
- **运行快照**：在响应中同步返回指标、进度与关键工件，方便外部系统消费。

## API 速览
| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `POST` | `/projects` | 新建训练项目。
| `GET` | `/projects` | 列出全部项目概览。
| `POST` | `/projects/{project_reference}/runs` | 基于项目 ID 或名称启动一次训练。

## API 请求示例

### 创建项目 `POST /projects`
- **功能**：登记一个新的训练项目并保存其配置。
- **请求体**：

  ```json
  {
    "name": "qwen-pretrain",
    "description": "Qwen 预训练任务",
    "owner": "alice",
    "tags": ["nlp", "pretrain"],
    "dataset_name": "datasets/qwen_mix.parquet",
    "training_yaml_name": "configs/qwen_pretrain.yaml"
  }
  ```
- **成功响应示例** (`201 Created`)：

  ```json
  {
    "id": "4c6f3f98-2417-4d8f-8ab5-ea81bc8b9179",
    "name": "qwen-pretrain",
    "description": "Qwen 预训练任务",
    "owner": "alice",
    "tags": ["nlp", "pretrain"],
    "dataset_name": "datasets/qwen_mix.parquet",
    "training_yaml_name": "configs/qwen_pretrain.yaml",
    "status": "active",
    "created_at": "2024-03-20T06:32:14.027Z",
    "updated_at": "2024-03-20T06:32:14.027Z",
    "runs_started": 0,
    "runs": []
  }
  ```

### 查询项目列表 `GET /projects`
- **功能**：检索所有项目的概要信息，常用于前端列表或自动化巡检。
- **入参**：无需请求体。
- **成功响应示例** (`200 OK`)：

  ```json
  [
    {
      "id": "4c6f3f98-2417-4d8f-8ab5-ea81bc8b9179",
      "name": "qwen-pretrain",
      "description": "Qwen 预训练任务",
      "owner": "alice",
      "tags": ["nlp", "pretrain"],
      "dataset_name": "datasets/qwen_mix.parquet",
      "training_yaml_name": "configs/qwen_pretrain.yaml",
      "status": "active",
      "created_at": "2024-03-20T06:32:14.027Z",
      "updated_at": "2024-03-20T06:32:14.027Z",
      "runs_started": 1
    }
  ]
  ```

### 触发训练运行 `POST /projects/{project_reference}/runs`
- **功能**：针对指定项目启动一次训练，`project_reference` 可使用项目 ID 或项目名称。
- **入参**：路径参数 `project_reference`，无需请求体。
- **成功响应示例** (`201 Created`)：

  ```json
  {
    "id": "0a3ce3b0-7f91-4c79-8b0e-2cbf9f7d88d9",
    "project_id": "4c6f3f98-2417-4d8f-8ab5-ea81bc8b9179",
    "status": "running",
    "created_at": "2024-03-20T06:35:11.482Z",
    "updated_at": "2024-03-20T06:35:11.719Z",
    "started_at": "2024-03-20T06:35:11.719Z",
    "completed_at": null,
    "progress": 0.05,
    "metrics": {},
    "start_command": "bash run_train_full_sft.sh configs/qwen_pretrain.yaml",
    "artifacts": [
      {
        "id": "f180f7f9-9e25-4c6f-85a5-6126d71b1b3c",
        "name": "checkpoint_step_0.pt",
        "type": "checkpoint",
        "path": "s3://artifacts/4c6f3f98-2417-4d8f-8ab5-ea81bc8b9179/0a3ce3b0-7f91-4c79-8b0e-2cbf9f7d88d9/checkpoint_step_0.pt",
        "created_at": "2024-03-20T06:35:11.482Z",
        "tags": []
      }
    ],
    "logs": [
      {
        "timestamp": "2024-03-20T06:35:11.482Z",
        "level": "INFO",
        "message": "Run created"
      },
      {
        "timestamp": "2024-03-20T06:35:11.482Z",
        "level": "INFO",
        "message": "Initializing resources"
      },
      {
        "timestamp": "2024-03-20T06:35:11.482Z",
        "level": "INFO",
        "message": "Loading dataset"
      },
      {
        "timestamp": "2024-03-20T06:35:11.482Z",
        "level": "INFO",
        "message": "Starting training loop"
      },
      {
        "timestamp": "2024-03-20T06:35:11.719Z",
        "level": "INFO",
        "message": "已确认训练资源数据集 datasets/qwen_mix.parquet，配置 configs/qwen_pretrain.yaml"
      },
      {
        "timestamp": "2024-03-20T06:35:11.719Z",
        "level": "INFO",
        "message": "已触发训练命令：bash run_train_full_sft.sh configs/qwen_pretrain.yaml (PID 42173)"
      }
    ],
    "resume_source_artifact_id": null
  }
  ```

## 快速开始
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后可通过 <http://localhost:8000/docs> 在浏览器中调试接口。

## 存储说明
项目默认使用内存存储（`InMemoryStorage`）模拟数据库与调度行为，服务重启后数据会丢失。可按需替换为真实的数据库和任务编排实现，以满足生产环境需求。
