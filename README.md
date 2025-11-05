# LLM 训练管理 API

本仓库提供了一个基于 FastAPI 的服务，用于管理大语言模型（LLM）训练项目及其生命周期。该服务覆盖了从定义训练项目，到发起、监控、取消、恢复训练运行的核心工作流，并在运行详情中返回生成的工件概览。

## 目录
- [功能亮点](#功能亮点)
- [架构概览](#架构概览)
  - [目录结构](#目录结构)
  - [模块职责](#模块职责)
  - [请求处理流程](#请求处理流程)
  - [扩展建议](#扩展建议)
- [快速开始](#快速开始)
- [运行 API](#运行-api)
- [API 参考](#api-参考)
  - [创建项目](#创建项目)
  - [列出项目](#列出项目)
  - [创建训练运行](#创建训练运行)
  - [获取运行详情](#获取运行详情)
  - [取消运行](#取消运行)
  - [恢复运行](#恢复运行)
- [内存存储行为](#内存存储行为)
- [开发提示](#开发提示)

## 功能亮点
- 定义项目元数据，例如名称、描述、目标、任务类型、负责人以及绑定的数据集和训练 YAML（需求 5.2.1）。
- 列出项目概览，查看状态、负责人和创建时间等关键信息（需求 5.2.2 精简版）。
- 启动新的训练运行，仅需提供启动命令，接口会校验项目数据集与 YAML 是否就绪，并在目标 Docker 容器内执行训练脚本（需求 5.2.3）。
- 监控训练进度，包括状态、指标、时间戳和 GPU 使用情况（需求 5.2.4）。
- 取消正在运行的训练，同时保留最新的检查点（需求 5.2.5）。
- 从选定的检查点恢复训练（需求 5.2.8）。

## 架构概览
LLM 训练管理 API 保持了极简但清晰的三层结构：路由层、领域模型层与存储层。你可以通过下文了解代码如何组织与协作。

### 目录结构
```
app/
├── __init__.py          # 标记包，方便后续拓展子模块
├── main.py              # 应用入口，暴露 FastAPI 实例并挂载所有路由
├── models.py            # Pydantic 数据模型，确保请求/响应结构一致
└── storage.py           # InMemoryStorage，模拟持久化与调度行为
```

### 模块职责
| 模块 | 关键职责 | 代表对象/函数 |
| --- | --- | --- |
| `app.main` | 初始化 FastAPI、注册路由、定义依赖注入。 | `app`, `get_storage`, 各类路由处理函数 |
| `app.models` | 描述领域实体，提供请求体验证、响应序列化以及默认值。 | `ProjectCreate`, `RunCreate`, `RunDetail`, `Artifact` 等 |
| `app.storage` | 模拟数据库 + 任务编排：生成 ID、维护项目状态、虚拟化日志/指标/工件。 | `InMemoryStorage`, `create_project`, `create_run`, `cancel_run` |

> **提示：** `InMemoryStorage` 使用 Python 内存保存所有数据，服务重启会导致信息丢失，适合演示或单元测试阶段。

### 请求处理流程
1. **HTTP 入口**：客户端调用 REST 接口，FastAPI 在 `app.main` 中匹配路由。
2. **请求解析**：请求体会被对应的 Pydantic 模型（定义在 `app.models`）自动校验并转化为 Python 对象。
3. **业务逻辑**：路由函数通过依赖注入 (`Depends(get_storage)`) 获取 `InMemoryStorage` 实例并执行增删改查逻辑。
4. **响应生成**：操作结果再度通过模型序列化为 JSON，统一的状态码由 FastAPI 自动处理。

### 扩展建议
- **持久化**：将 `InMemoryStorage` 替换为数据库实现（如 PostgreSQL、MongoDB），同时把任务调度对接到真实的队列/编排器。
- **服务拆分**：当业务增长时，可将路由按领域拆分为独立模块（如 `routers/projects.py`），并引入分层服务类以复用业务逻辑。
- **观测性**：在路由层添加日志、追踪与指标收集钩子，便于集成 Prometheus 或 OpenTelemetry。
- **配置管理**：通过环境变量或配置文件（如 `pydantic-settings`）管理存储后端、认证开关等环境信息。

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
- **功能描述：** 创建一个新的训练项目并保存其元数据（需求 5.2.1）。
- **入参：**
  - **路径参数：** 无。
  - **查询参数：** 无。
  - **请求体（JSON）：**

    | 字段 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `name` | string | 是 | 项目名称，需全局唯一。 |
    | `description` | string | 否 | 项目摘要，用于说明背景与需求。 |
    | `objective` | string | 是 | 训练目标或关键指标。 |
    | `task_type` | string | 是 | 任务类型，例如“文本摘要”“问答”。 |
    | `owner` | string | 是 | 负责人名称或工号。 |
    | `dataset_name` | string | 是 | 项目关联的数据集名称或标识。 |
    | `training_yaml_name` | string | 是 | 训练配置文件（YAML）的名称。 |
    | `tags` | array[string] | 否 | 自定义标签，便于分类检索。 |

  - **示例请求体：**
    ```json
    {
      "name": "印章大模型",
      "description": "构建印章通用大模型",
      "objective": "初版模型训练",
      "task_type": "VL-Lora",
      "owner": "LL",
      "dataset_name": "seal-documents-v1",
      "training_yaml_name": "seal-train.yaml",
      "tags": ["VL", "通用印章"]
    }
    ```
- **出参：** `201 Created`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 项目唯一标识，形如 `proj_xxx`。 |
    | `name` | string | 项目名称。 |
    | `description` | string | 项目摘要。 |
    | `status` | string | 当前状态，取值：`active` 或 `archived`。 |
    | `objective` | string | 训练目标。 |
    | `task_type` | string | 任务类型。 |
    | `owner` | string | 负责人。 |
    | `dataset_name` | string | 项目关联的数据集名称或标识。 |
    | `training_yaml_name` | string | 训练配置文件名称。 |
    | `created_at` | datetime | 创建时间（ISO 8601）。 |
    | `updated_at` | datetime | 更新时间（ISO 8601）。 |
    | `runs_started` | integer | 已创建的运行数量。 |
    | `tags` | array[string] | 标签列表。 |
    | `runs` | array[object] | 与项目关联的运行列表。 |

  - **响应示例：**
    ```json
    {
      "id": "proj_xxx",
      "name": "印章大模型",
      "status": "active",
      "objective": "初版模型训练",
      "task_type": "VL-Lora",
      "owner": "LL",
      "dataset_name": "seal-documents-v1",
      "training_yaml_name": "seal-train.yaml",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "runs_started": 0,
      "tags": ["VL", "通用印章"],
      "runs": []
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "印章大模型",
          "description": "构建印章通用大模型",
          "objective": "初版模型训练",
          "task_type": "VL-Lora",
          "owner": "LL",
          "dataset_name": "seal-documents-v1",
          "training_yaml_name": "seal-train.yaml",
          "tags": ["VL", "通用印章"]
        }'
  ```

### 列出项目
- **方法与路径：** `GET /projects`
- **功能描述：** 获取所有项目的摘要列表。
- **入参：**
  - **路径参数：** 无。
  - **查询参数：** 无。
- **出参：** `200 OK`
  - **响应体：** 项目对象数组，每个对象包含：

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 项目唯一标识。 |
    | `name` | string | 项目名称。 |
    | `status` | string | 项目状态，取值：`active` 或 `archived`。 |
    | `owner` | string | 负责人。 |
    | `dataset_name` | string | 项目关联的数据集名称或标识。 |
    | `training_yaml_name` | string | 训练配置文件名称。 |
    | `created_at` | datetime | 创建时间。 |
    | `updated_at` | datetime | 最近更新时间。 |
    | `runs_started` | integer | 已创建的运行数量。 |
    | `objective` | string | 训练目标。 |
    | `task_type` | string | 任务类型。 |
    | `tags` | array[string] | 标签列表。 |

  - **响应示例：**
    ```json
    [
      {
        "id": "proj_xxx",
        "name": "中文摘要系统",
        "status": "active",
        "owner": "小李",
        "dataset_name": "cn-summarization-v2",
        "training_yaml_name": "summarization-train.yaml",
        "objective": "降低阅读时间",
        "task_type": "文本摘要",
        "tags": ["科研", "第一阶段"],
        "runs_started": 1,
        "created_at": "2024-01-01T12:00:00Z",
        "updated_at": "2024-01-02T09:30:00Z"
      }
    ]
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects"
  ```

### 创建训练运行
- **方法与路径：** `POST /projects/{project_reference}/runs`
- **功能描述：** 为项目创建新的训练运行（需求 5.2.3）。接口接受项目的 **ID 或名称** 作为路径参数，并会读取项目绑定的 `dataset_name` 与 `training_yaml_name`，先在宿主机
  `/data1/qwen2.5-14bxxxx` 下确认对应的数据集和 YAML 文件均已上传，再按照如下顺序调度训练：

  1. `cd /data1/qwen2.5-14bxxxx`
  2. `docker exec -i qwen2.5-14b-instruct_xpytorch_full_sft env LANG=C.UTF-8 bash`
  3. 在容器中执行 `cd KTIP_Release_2.1.0/train/llm`
  4. 运行请求体中提供的启动命令（例如 `bash run_train_full_sft.sh train.yaml`）

  训练会以后台进程方式启动，接口立即返回；若命令无法启动，会返回 `500` 错误并将运行标记为 `failed`。若数据集或 YAML 未找到，接口会返回
  `400` 并给出缺失项。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_reference` | string | 是 | 目标项目的唯一 ID 或名称。若名称包含空格，请使用 URL 编码。 |

  - **请求体（JSON）：**

    | 字段 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `start_command` | string | 是 | 在容器内执行的训练命令，例如 `bash run_train_full_sft.sh train.yaml`。 |

  - **示例请求体：**
    ```json
    {
      "start_command": "bash run_train_full_sft.sh seal-train.yaml"
    }
    ```
- **说明：** 请求体无需再传入数据集或 YAML 名称，系统会根据项目配置自动完成校验。
- **出参：** `201 Created`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 运行唯一标识。 |
    | `project_id` | string | 所属项目 ID。 |
    | `status` | string | 当前状态，可能的取值：`pending`、`running`、`completed`、`failed`、`canceled`、`paused`。 |
    | `created_at` | datetime | 创建时间。 |
    | `updated_at` | datetime | 最近更新时间。 |
    | `started_at` | datetime/null | 启动时间。 |
    | `completed_at` | datetime/null | 完成或终止时间。 |
    | `progress` | float | 运行进度（0–1）。 |
    | `metrics` | object | 模拟的指标字典。 |
    | `start_command` | string | 实际触发的训练命令。 |
    | `artifacts` | array[object] | 运行关联的工件列表。 |
    | `logs` | array[object] | 模拟生成的日志条目。 |
    | `resume_source_artifact_id` | string/null | 若为恢复运行，指向使用的检查点 ID。 |

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "status": "running",
      "created_at": "2024-01-02T08:00:00Z",
      "updated_at": "2024-01-02T08:00:00Z",
      "started_at": "2024-01-02T08:00:00Z",
      "completed_at": null,
      "progress": 0.05,
      "metrics": {},
      "start_command": "bash run_train_full_sft.sh seal-train.yaml",
      "artifacts": [
        {
          "id": "art_ckpt",
          "name": "checkpoint_step_0.pt",
          "type": "checkpoint",
          "path": "s3://artifacts/proj_xxx/run_001/checkpoint_step_0.pt",
          "created_at": "2024-01-02T08:00:00Z",
          "tags": []
        },
        {
          "id": "art_tb",
          "name": "events.out.tfevents",
          "type": "tensorboard",
          "path": "s3://artifacts/proj_xxx/run_001/events.out.tfevents",
          "created_at": "2024-01-02T08:00:00Z",
          "tags": []
        },
        {
          "id": "art_cfg",
          "name": "training_config.yaml",
          "type": "config",
          "path": "s3://artifacts/proj_xxx/run_001/training_config.yaml",
          "created_at": "2024-01-02T08:00:00Z",
          "tags": []
        }
      ],
      "logs": [
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "Run created"
        },
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "Initializing resources"
        },
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "Loading dataset"
        },
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "Starting training loop"
        },
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "已确认训练资源数据集 seal-documents-v1，配置 seal-train.yaml"
        },
        {
          "timestamp": "2024-01-02T08:00:00Z",
          "level": "INFO",
          "message": "已触发训练命令：bash run_train_full_sft.sh seal-train.yaml (PID 4242)"
        }
      ],
      "resume_source_artifact_id": null
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs" \
    -H "Content-Type: application/json" \
    -d '{
          "start_command": "bash run_train_full_sft.sh seal-train.yaml"
        }'
  ```

  ```bash
  curl -X POST "http://localhost:8000/projects/%E4%B8%AD%E6%96%87%E6%91%98%E8%A6%81%E7%B3%BB%E7%BB%9F/runs" \
    -H "Content-Type: application/json" \
    -d '{
          "start_command": "bash run_train_full_sft.sh seal-train.yaml"
        }'
  ```

### 获取运行详情
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}`
- **功能描述：** 查看指定运行的状态、指标以及生成的工件与日志（需求 5.2.4）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
- **出参：** `200 OK`
  - **响应体字段：** 返回与 [创建训练运行](#创建训练运行) 相同的 `RunDetail` 结构，包含状态、指标、启动命令、工件、日志以及 `resume_source_artifact_id` 等信息。

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "status": "running",
      "created_at": "2024-01-02T08:05:00Z",
      "updated_at": "2024-01-02T10:15:00Z",
      "started_at": "2024-01-02T08:05:00Z",
      "completed_at": null,
      "progress": 0.65,
      "metrics": {
        "train_loss": 1.72,
        "eval_rouge_l": 38.4
      },
      "start_command": "bash run_train_full_sft.sh seal-train.yaml",
      "artifacts": [
        {
          "id": "ckpt_001",
          "name": "checkpoint_step_0.pt",
          "type": "checkpoint",
          "path": "s3://artifacts/proj_xxx/run_001/checkpoint_step_0.pt",
          "created_at": "2024-01-02T08:05:00Z",
          "tags": []
        }
      ],
      "logs": [
        {
          "timestamp": "2024-01-02T08:05:00Z",
          "level": "INFO",
          "message": "Run created"
        }
      ],
      "resume_source_artifact_id": null
    }
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects/proj_xxx/runs/run_001"
  ```

### 取消运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/cancel`
- **功能描述：** 取消正在执行的运行并保存最新检查点（需求 5.2.5）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
- **出参：** `200 OK`
  - **响应体字段：** 返回更新后的 `RunDetail` 对象，`status` 将变为 `canceled`，`completed_at` 会记录取消时间，工件列表会包含取消时生成的检查点。

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "status": "canceled",
      "created_at": "2024-01-02T08:05:00Z",
      "updated_at": "2024-01-02T11:00:00Z",
      "started_at": "2024-01-02T08:05:00Z",
      "completed_at": "2024-01-02T11:00:00Z",
      "progress": 0.7,
      "metrics": {
        "train_loss": 1.2
      },
      "start_command": "bash run_train_full_sft.sh seal-train.yaml",
      "artifacts": [
        {
          "id": "ckpt_cancel",
          "name": "checkpoint_step_0.pt",
          "type": "checkpoint",
          "path": "s3://artifacts/proj_xxx/run_001/checkpoint_step_0.pt",
          "created_at": "2024-01-02T08:05:00Z",
          "tags": []
        }
      ],
      "logs": [
        {
          "timestamp": "2024-01-02T11:00:00Z",
          "level": "INFO",
          "message": "Run canceled"
        }
      ],
      "resume_source_artifact_id": null
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs/run_001/cancel"
  ```

### 恢复运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/resume`
- **功能描述：** 从已有检查点恢复或继续训练（需求 5.2.8）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 原运行所属项目 ID。 |
    | `run_id` | string | 是 | 原运行 ID。 |

  - **查询参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `source_artifact_id` | string | 是 | 要恢复的检查点工件 ID。 |

  - **请求体（JSON）：** 结构与 [创建训练运行](#创建训练运行) 一致，通过 `start_command` 字段提供新的启动命令。

- **出参：** `201 Created`
  - **响应体字段：** 返回新的 `RunDetail`，其 `resume_source_artifact_id` 会设置为查询参数提供的工件 ID，其余字段与创建运行一致。

  - **响应示例：**
    ```json
    {
      "id": "run_002",
      "project_id": "proj_xxx",
      "status": "running",
      "created_at": "2024-01-03T08:00:00Z",
      "updated_at": "2024-01-03T08:00:00Z",
      "started_at": "2024-01-03T08:00:00Z",
      "completed_at": null,
      "progress": 0.05,
      "metrics": {},
      "start_command": "bash run_train_full_sft.sh seal-train.yaml",
      "artifacts": [],
      "logs": [
        {
          "timestamp": "2024-01-03T08:00:00Z",
          "level": "INFO",
          "message": "Run created"
        }
      ],
      "resume_source_artifact_id": "ckpt_001"
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs/run_001/resume?source_artifact_id=ckpt_001" \
    -H "Content-Type: application/json" \
    -d '{
          "start_command": "bash run_train_full_sft.sh seal-train.yaml"
        }'
  ```

## 内存存储行为
示例存储层刻意保持简单：
- ID 使用简短前缀自动生成（如 `proj_`、`run_`、`ckpt_`）。
- 运行会自动生成模拟的指标、日志和工件，这些内容会直接体现在 `RunDetail` 响应中。
- 取消运行会将状态改为 `canceled` 并产生一个最终检查点。
- 恢复运行会克隆原运行的启动命令并关联到源检查点。

在生产环境中，请将 `app/storage.py` 替换为与你的数据库、作业调度、监控与工件系统相连接的实现。

## 开发提示
- 使用 `app/models.py` 中的 Pydantic 模型作为客户端/服务端通信契约。
- 可以扩展 `InMemoryStorage`，或将其替换为持久化存储以满足真实部署需求。
- 按需增加认证、鉴权和多租户隔离能力。
- 考虑增加后台任务或 Celery 等框架以支持更长耗时的训练编排。
