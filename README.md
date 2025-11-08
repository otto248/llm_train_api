# LLM 训练管理 API

一个基于 FastAPI 的轻量级服务，用于集中管理大模型训练项目并触发运行命令。服务通过结构化的“项目”“运行”“日志”“工件”模型，帮助训练平台快速搭建统一的编排层，便于与现有的训练脚本或调度系统集成。

## 功能概览
- **项目管理**：登记训练项目的基本信息（名称、负责人、数据集、训练配置等），并持久化保存。项目默认处于 `active` 状态，可扩展为归档等流程。【F:app/models.py†L10-L49】【F:app/storage.py†L67-L123】
- **运行管理**：为任意项目创建新的训练运行，记录启动命令、运行状态、进度、指标及关联系统日志/工件。【F:app/main.py†L70-L135】【F:app/storage.py†L124-L326】
- **日志与工件**：运行创建时自动补充示例日志与工件，便于前端或外部系统演示展示，也支持追加标签、分页查询等存储能力。【F:app/storage.py†L327-L567】

## API 端点
| 方法 | 路径 | 描述 |
| ---- | ---- | ---- |
| `POST` | `/projects` | 创建新的训练项目，返回项目详情及空运行列表。【F:app/main.py†L99-L104】 |
| `GET` | `/projects` | 列出全部训练项目的概要信息。【F:app/main.py†L107-L111】 |
| `POST` | `/projects/{project_reference}/runs` | 根据项目 ID 或名称触发一次训练运行，校验数据集/配置文件存在并异步执行训练脚本。【F:app/main.py†L114-L159】 |

所有端点均返回 Pydantic 模型封装的结构化数据，详细字段定义可参考 `app/models.py`。【F:app/models.py†L10-L132】

## 训练命令执行流程
1. **项目资源校验**：创建运行前，会检查项目中声明的 `dataset_name` 与 `training_yaml_name` 是否存在于宿主机的训练目录（默认 `/data1/qwen2.5-14bxxxx`）。若缺失，将返回 400 错误提示缺少的资源。【F:app/main.py†L59-L87】
2. **启动命令构建**：服务默认拼接 `bash run_train_full_sft.sh <training_yaml>` 作为启动命令，可根据需要修改 `_build_start_command` 的实现。【F:app/main.py†L50-L56】
3. **Docker 内执行**：训练命令通过 `docker exec` 在指定容器（默认 `qwen2.5-14b-instruct_xpytorch_full_sft`）及工作目录（默认 `KTIP_Release_2.1.0/train/llm`）中执行。命令在独立的 bash 会话中启动，标准输出/错误被忽略，可根据需要定制重定向策略。【F:app/main.py†L26-L48】
4. **运行状态更新**：启动成功后，服务会写入确认日志，并将运行状态更新为 `running`，初始进度为 0.05。若命令启动失败，会记录错误日志并将运行标记为 `failed`。【F:app/main.py†L135-L159】

> 💡 在部署时，可根据实际环境调整 `_HOST_TRAINING_DIR`、`_DOCKER_CONTAINER_NAME` 与 `_DOCKER_WORKING_DIR` 常量，以匹配真实的宿主机目录与容器名称。【F:app/main.py†L21-L37】

## 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（默认端口 8000）
uvicorn app.main:app --reload
```
启动后可通过 <http://localhost:8000/docs> 查看自动生成的 Swagger UI 并调试接口。

### 数据库存储配置
- **默认配置**：若未设置环境变量，服务会使用本地 `sqlite:///./training.db` 文件存储所有项目、运行、日志与工件记录。【F:app/storage.py†L39-L43】【F:app/storage.py†L86-L123】
- **自定义数据库**：部署时可设置 `TRAINING_DB_URL` 指向任意兼容 SQLAlchemy 的数据库（如 PostgreSQL、MySQL 等）。服务启动时会自动创建所需的四张表：`projects`、`runs`、`logs`、`artifacts`。【F:app/storage.py†L39-L83】

## 本地开发建议
1. **准备训练目录**：在宿主机上创建 `_HOST_TRAINING_DIR` 对应的路径，确保示例数据集与训练配置文件存在（或调整常量指向本地测试路径）。【F:app/main.py†L21-L37】【F:app/main.py†L59-L87】
2. **验证数据库**：首次运行会自动生成 SQLite 文件；若切换数据库，请确认网络、权限与凭据设置正确。
3. **调试命令执行**：为了安全性，默认训练命令在后台静默运行。需要实时查看日志时，可以修改 `_launch_training_process` 将 `stdout`/`stderr` 重定向到文件或管道。

## 后续扩展方向
- 暴露运行详情、日志分页、工件标签等 API（存储层已具备相关能力）。【F:app/storage.py†L327-L567】
- 接入任务编排系统或消息队列，实现分布式训练调度。
- 将训练命令执行抽象为接口，以支持不同类型的执行后端（例如 Kubernetes Job、Slurm 等）。

欢迎根据业务需求进行定制与扩展！
