# LLM 训练管理 API

本仓库提供了一个基于 FastAPI 的服务，用于管理大语言模型（LLM）训练项目及其生命周期。该服务覆盖了从定义训练项目，到发起、监控、取消、恢复训练运行，以及管理生成的工件等完整工作流。

## 目录
- [功能亮点](#功能亮点)
- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [运行 API](#运行-api)
- [API 参考](#api-参考)
  - [创建项目](#创建项目)
  - [列出项目](#列出项目)
  - [获取项目详情](#获取项目详情)
  - [创建训练运行](#创建训练运行)
  - [获取运行详情](#获取运行详情)
  - [取消运行](#取消运行)
  - [获取运行日志](#获取运行日志)
  - [列出运行工件](#列出运行工件)
  - [恢复运行](#恢复运行)
  - [为工件打标签](#为工件打标签)
- [内存存储行为](#内存存储行为)
- [开发提示](#开发提示)

## 功能亮点
- 定义项目元数据，例如名称、描述、目标、任务类型、基线模型和负责人（需求 5.2.1）。
- 查看项目状态、运行次数、默认配置、版本历史和关联的运行（需求 5.2.2）。
- 启动新的训练运行，包括模型、数据集、超参数和资源配置（需求 5.2.3）。
- 监控训练进度，包括状态、指标、时间戳和 GPU 使用情况（需求 5.2.4）。
- 取消正在运行的训练，同时保留最新的检查点（需求 5.2.5）。
- 获取支持分页和时间过滤的日志（需求 5.2.6）。
- 列出工件（检查点、TensorBoard 日志、评估结果、配置文件）（需求 5.2.7）。
- 从选定的检查点恢复训练（需求 5.2.8）。
- 将检查点标记为候选基线模型或发布版本（需求 5.2.9）。

## 架构概览
FastAPI 服务主要由以下三个模块组成：

| 模块 | 说明 |
| --- | --- |
| `app/main.py` | 声明 FastAPI 应用并注册全部 REST 端点。 |
| `app/models.py` | 定义用于校验与序列化的 Pydantic 请求/响应模型。 |
| `app/storage.py` | 实现一个模拟项目、运行、日志、指标与工件的内存存储层。 |

> **注意：** 存储层仅在进程存活期间保留数据，重启服务将清空全部状态。

## 快速开始
安装依赖（推荐使用 Python 3.10 及以上版本）：

```bash
pip install -r requirements.txt
```

可选的快速语法检查：

```bash
python -m compileall app
```

## 运行 API
启动开发服务器：

```bash
uvicorn app.main:app --reload
```

OpenAPI/Swagger UI 可通过 <http://localhost:8000/docs> 访问。你也可以使用 Postman 或任意 HTTP 客户端与 API 交互。

## API 参考
所有端点均返回 JSON 响应并使用标准 HTTP 状态码。除非另有说明，请以 JSON 格式提交请求体。

### 创建项目
- **方法与路径：** `POST /projects`
- **说明：** 创建一个新的训练项目并保存其元数据（需求 5.2.1）。
- **请求体：**
  ```json
  {
    "name": "中文摘要系统",
    "description": "对科研文章进行自动摘要",
    "objective": "降低阅读时间",
    "task_type": "文本摘要",
    "base_model": "llama-2-13b",
    "owner": "小李",
    "tags": ["科研", "第一阶段"],
    "default_hyperparameters": {
      "learning_rate": 3e-5,
      "batch_size": 16
    }
  }
  ```
- **响应：** `201 Created`
  ```json
  {
    "id": "proj_xxx",
    "name": "中文摘要系统",
    "status": "草稿",
    "objective": "降低阅读时间",
    "task_type": "文本摘要",
    "base_model": "llama-2-13b",
    "owner": "小李",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z",
    "tags": ["科研", "第一阶段"],
    "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
    "runs": []
  }
  ```

### 列出项目
- **方法与路径：** `GET /projects`
- **说明：** 获取所有项目的摘要列表。
- **响应：** `200 OK`
  ```json
  [
    {
      "id": "proj_xxx",
      "name": "中文摘要系统",
      "status": "草稿",
      "owner": "小李",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
  ```

### 获取项目详情
- **方法与路径：** `GET /projects/{project_id}`
- **说明：** 查看指定项目的全部信息（需求 5.2.2）。
- **响应：** `200 OK`
  ```json
  {
    "id": "proj_xxx",
    "name": "中文摘要系统",
    "status": "草稿",
    "objective": "降低阅读时间",
    "task_type": "文本摘要",
    "base_model": "llama-2-13b",
    "owner": "小李",
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-02T09:30:00Z",
    "tags": ["科研", "第一阶段"],
    "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
    "runs": [
      {
        "id": "run_001",
        "name": "run-001",
        "status": "运行中",
        "progress": 0.42,
        "started_at": "2024-01-02T08:00:00Z"
      }
    ]
  }
  ```

### 创建训练运行
- **方法与路径：** `POST /projects/{project_id}/runs`
- **说明：** 为项目创建新的训练运行（需求 5.2.3）。
- **请求体：**
  ```json
  {
    "name": "run-001",
    "model": "llama-2-13b",
    "dataset": "中文科技论文语料",
    "hyperparameters": {
      "learning_rate": 2e-5,
      "batch_size": 32,
      "num_epochs": 3
    },
    "resources": {
      "gpu_type": "A100",
      "gpu_count": 4
    }
  }
  ```
- **响应：** `201 Created`
  ```json
  {
    "id": "run_001",
    "project_id": "proj_xxx",
    "name": "run-001",
    "status": "排队中",
    "progress": 0.0,
    "started_at": null,
    "artifacts": []
  }
  ```

### 获取运行详情
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}`
- **说明：** 查看指定运行的状态与指标（需求 5.2.4）。
- **响应：** `200 OK`
  ```json
  {
    "id": "run_001",
    "project_id": "proj_xxx",
    "name": "run-001",
    "status": "运行中",
    "progress": 0.65,
    "metrics": {
      "train_loss": 1.72,
      "eval_rouge_l": 38.4
    },
    "started_at": "2024-01-02T08:05:00Z",
    "updated_at": "2024-01-02T10:15:00Z",
    "gpu_utilization": 0.83
  }
  ```

### 取消运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/cancel`
- **说明：** 取消正在执行的运行并保存最新检查点（需求 5.2.5）。
- **响应：** `200 OK`
  ```json
  {
    "id": "run_001",
    "project_id": "proj_xxx",
    "name": "run-001",
    "status": "已取消",
    "progress": 0.7,
    "cancelled_at": "2024-01-02T11:00:00Z",
    "artifacts": [
      {
        "id": "ckpt_cancel",
        "name": "取消前的检查点",
        "type": "checkpoint",
        "path": "s3://artifacts/proj_xxx/run_001/ckpt_cancel.pt",
        "created_at": "2024-01-02T11:00:00Z"
      }
    ]
  }
  ```

### 获取运行日志
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}/logs`
- **说明：** 获取运行日志，支持分页与可选的时间范围过滤（需求 5.2.6）。
- **查询参数：**
  | 名称 | 类型 | 默认值 | 说明 |
  | --- | --- | --- | --- |
  | `page` | integer | `1` | 页码（从 1 开始）。 |
  | `page_size` | integer | `50` | 每页日志数量（1–500）。 |
  | `start_time` | ISO 8601 datetime | `null` | 筛选在此时间或之后的日志。 |
  | `end_time` | ISO 8601 datetime | `null` | 筛选在此时间之前的日志。 |
- **响应：** `200 OK`
  ```json
  {
    "page": 1,
    "page_size": 50,
    "total": 120,
    "items": [
      {
        "timestamp": "2024-01-02T10:00:00Z",
        "level": "INFO",
        "message": "第 500 步 - loss=1.86 lr=2e-5"
      }
    ]
  }
  ```

### 列出运行工件
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}/artifacts`
- **说明：** 列出运行生成的检查点和其他输出（需求 5.2.7）。
- **响应：** `200 OK`
  ```json
  {
    "items": [
      {
        "id": "ckpt_001",
        "name": "第 2000 步检查点",
        "type": "checkpoint",
        "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
        "created_at": "2024-01-02T11:45:00Z",
        "size_bytes": 123456789,
        "tags": []
      },
      {
        "id": "log_tensorboard",
        "name": "TensorBoard 日志",
        "type": "event",
        "path": "s3://artifacts/proj_xxx/run_001/tensorboard",
        "created_at": "2024-01-02T11:50:00Z",
        "tags": []
      }
    ]
  }
  ```

### 恢复运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/resume`
- **说明：** 从已有检查点恢复或继续训练（需求 5.2.8）。
- **查询参数：**
  | 名称 | 类型 | 必填 | 说明 |
  | --- | --- | --- | --- |
  | `source_artifact_id` | string | 是 | 要恢复的检查点工件 ID。 |
- **请求体：** 与 [创建训练运行](#创建训练运行) 相同，允许为恢复的运行覆盖超参数。
- **响应：** `201 Created`
  ```json
  {
    "id": "run_002",
    "project_id": "proj_xxx",
    "name": "run-002",
    "status": "运行中",
    "resumed_from": "ckpt_001",
    "progress": 0.05,
    "started_at": "2024-01-03T08:00:00Z",
    "artifacts": []
  }
  ```

### 为工件打标签
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/tag`
- **说明：** 将检查点标记为候选基线模型或发布版本（需求 5.2.9）。
- **请求体：**
  ```json
  {
    "tag": "发布",
    "notes": "在验证集上 BLEU 32.5，通过复核"
  }
  ```
  可用标签：`候选`、`发布`、`归档`。
- **响应：** `200 OK`
  ```json
  {
    "id": "ckpt_001",
    "name": "第 2000 步检查点",
    "type": "checkpoint",
    "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
    "created_at": "2024-01-02T11:45:00Z",
    "tags": [
      {
        "value": "发布",
        "notes": "在验证集上 BLEU 32.5，通过复核",
        "applied_at": "2024-01-03T09:15:00Z"
      }
    ]
  }
  ```

## 内存存储行为
示例存储层刻意保持简单：
- ID 使用简短前缀自动生成（如 `proj_`、`run_`、`ckpt_`）。
- 运行会自动生成模拟的指标、日志和工件。
- 取消运行会将状态改为 `已取消` 并产生一个最终检查点。
- 恢复运行会克隆原运行的配置并关联到源检查点。

在生产环境中，请将 `app/storage.py` 替换为与你的数据库、作业调度、监控与工件系统相连接的实现。

## 开发提示
- 使用 `app/models.py` 中的 Pydantic 模型作为客户端/服务端通信契约。
- 可以扩展 `InMemoryStorage`，或将其替换为持久化存储以满足真实部署需求。
- 按需增加认证、鉴权和多租户隔离能力。
- 考虑增加后台任务或 Celery 等框架以支持更长耗时的训练编排。
