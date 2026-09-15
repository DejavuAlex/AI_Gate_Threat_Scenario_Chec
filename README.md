# AI Security Gate

AI Security Gate 是一个面向文档驱动研发流程的 AI 安全评审与威胁建模系统。它通过 Gate1 和 Gate2 两个阶段，对业务需求、架构设计、API 设计、数据模型和实现计划进行安全风险识别、控制措施生成、报告输出和评审流转。

当前项目支持三种调用方式：

1. **API 调用**：外部系统通过 HTTP API 触发 Gate1 / Gate2 Review。
2. **CI/CD Pipeline 调用**：流水线通过专用 CI/CD API 触发安全评审。
3. **CLI 本地 Agent 调用**：开发者在 VS Code、本地终端或脚本中单次调用 Gate1 / Gate2 Agent，直接获取本地 Review 结果。

---

## 1. 核心能力

### Gate1：业务需求安全评审

Gate1 面向业务需求阶段，读取以下类型文档：

```text
specs/product-requirements.md
specs/user-stories.md
specs/business-flow.md
```

Gate1 会：

- 读取 Gate1 金标准知识库
- 匹配业务威胁场景
- 识别业务安全风险
- 生成安全控制措施
- 输出 Gate1 安全评审结果
- 在平台工作流中支持报告、审批和后续 Gate2 触发

### Gate2：架构 / API / 技术需求安全评审

Gate2 面向架构和实现设计阶段，读取以下类型文档：

```text
specs/architecture.md
specs/api-design.md
specs/data-model.md
specs/implementation-plan.md
```

Gate2 会：

- 读取 Gate2 金标准知识库
- 匹配技术安全风险场景
- 可读取 Gate1 报告
- 验证 Gate1 安全控制措施是否落实到 Gate2 文档中
- 输出未落实项和优化建议
- 生成 Gate2 安全评审结果

### LLM 集成

系统支持 OpenAI-compatible LLM Gateway：

- 通过环境变量配置
- 不在仓库中保存 API Key
- LLM 仅作为辅助匹配、证据提取和控制措施优化层
- 金标准知识库页面支持对话生成同格式 Scenario 候选，并展示 `P1`、`P2`、`P`、`S`（存储字段为 `severity`）
- 候选必须由用户修改或确认、应用到 KB 编辑器，再通过人工同步写入知识库并记录变更历史
- LLM 调用失败时自动 fallback 到确定性匹配引擎
- LLM 不允许修改金标准知识库
- LLM 不允许降低阈值或强行匹配
- LLM 不允许自动 Approve 报告

---

## 2. 当前项目结构

```text
AI_Security_Gate/
  backend/
    app/
      main.py                    FastAPI 应用入口
      api.py                     REST API 路由
      config.py                  全局配置、路径、LLM 环境变量
      schemas.py                 Pydantic 请求/响应模型
      static/
        index.html               Web UI 页面
      services/
        documents.py             读取 Speckit / Markdown 文档
        knowledge_base.py        金标准知识库读取和人工保存
        matching.py              确定性匹配评分引擎
        llm_client.py            OpenAI-compatible LLM 客户端
        llm_matching.py          LLM 辅助匹配逻辑
        gate2_verifier.py        Gate2 验证 Gate1 控制措施
        report_generator.py      Markdown 报告生成器
        review.py                Gate1/Gate2 Review 编排服务

  cli/
    security_gate_cli.py         本地 CLI Agent 入口

  knowledge_base/
    gate1/
      default-gate1-knowledge-base.json
    gate2/
      default-gate2-knowledge-base.json

  specs/
    product-requirements.md      Gate1 示例业务需求文档
    user-stories.md              Gate1 示例用户故事
    business-flow.md             Gate1 示例业务流程
    architecture.md              Gate2 示例架构文档
    api-design.md                Gate2 示例 API 设计
    data-model.md                Gate2 示例数据模型
    implementation-plan.md       Gate2 示例实现计划

  reports/                       平台工作流生成的报告目录
  data/                          平台工作流生成的任务、评审和工单数据
  tests/                         自动化测试

  Dockerfile
  docker-compose.yml
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  .env.example
```

---

## 3. 安装配置指导

### 3.1 克隆仓库

```bash
git clone https://github.com/quy7_roche/AI_Security_Gate.git
cd AI_Security_Gate
```

### 3.2 创建虚拟环境

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows CMD：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3.3 安装依赖

```bash
pip install -r requirements.txt
```

如需运行测试：

```bash
pip install -r requirements-dev.txt
pytest -q
```

### 3.4 配置环境变量

复制示例配置：

```bash
cp .env.example .env
```

常用配置：

```env
AI_SECURITY_GATE_HOST_PORT=18080
AI_SECURITY_GATE_DOCS_PORT=18081
AI_SECURITY_GATE_API_KEY=replace-with-your-api-key

AI_LLM_ENABLED=false
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-2025-08-07
OPENAI_BASE_URL=https://eu.aigw.galileo.roche.com/v1
OPENAI_API_KEY=replace-with-your-secret-key
LLM_MATCHING_TEMPERATURE=0
LLM_MATCHING_TIMEOUT_SECONDS=60
```

说明：

- `AI_SECURITY_GATE_API_KEY` 仅用于外部 API 任务触发和 CI/CD Pipeline 调用。
- UI 内部调用不在浏览器保存或展示 API Key。
- CLI 本地 Agent 不需要 API Key。
- LLM 相关 Key 只应保存在本地环境变量或 `.env` 中，不应提交到仓库。

---

## 4. 启动服务

### 4.1 本地启动

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问：

```text
UI:   http://localhost:8000
Docs: http://localhost:8000/docs
```

### 4.2 Docker / Podman 启动

构建镜像：

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  -t localhost/ai-security-gate:latest .
```

运行容器：

```bash
podman run -d \
  --name ai-security-gate \
  -p 18080:8000 \
  -p 18081:8000 \
  -v ./reports:/app/reports:Z \
  -v ./data:/app/data:Z \
  -v ./knowledge_base:/app/knowledge_base:Z \
  -v ./specs:/app/specs:Z \
  --env-file .env \
  localhost/ai-security-gate:latest
```

访问：

```text
UI:        http://localhost:18080
API Docs:  http://localhost:18081/docs
```

### 4.3 docker compose 启动

```bash
docker compose up -d --build
```

默认端口：

```text
UI/API:   http://localhost:18080
API Docs: http://localhost:18081/docs
```

---

## 5. 调用方式

### 5.1 UI 调用

UI 页面入口：

```text
http://localhost:18080
```

在 UI 中进入：

```text
Threat Modeling Review
```

然后可分别执行：

```text
Gate1 Review
Gate2 Review
```

UI 使用内部接口：

```text
POST /api/v1/ui/security-review/gate1/run
POST /api/v1/ui/security-review/gate2/run
```

UI 内部接口不需要 API Key。

### 5.2 外部 API 调用

外部 API 触发任务需要 `AI_SECURITY_GATE_API_KEY`。

Gate1：

```bash
curl -X POST "http://localhost:18080/api/v1/security-review/gate1/run" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <AI_SECURITY_GATE_API_KEY>" \
  -d '{
    "project_id":"demo",
    "product_name":"Demo Security Gate Product",
    "product_version":"v1.0.0",
    "repository":"quy7_roche/AI_Security_Gate",
    "branch":"main",
    "documents":["specs/product-requirements.md","specs/user-stories.md","specs/business-flow.md"],
    "gate2_documents":["specs/architecture.md","specs/api-design.md","specs/data-model.md","specs/implementation-plan.md"],
    "threshold":0.78,
    "triggered_by":"api",
    "auto_run_gate2_on_gate1_approval":true
  }'
```

Gate2：

```bash
curl -X POST "http://localhost:18080/api/v1/security-review/gate2/run" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <AI_SECURITY_GATE_API_KEY>" \
  -d '{
    "project_id":"demo",
    "product_name":"Demo Security Gate Product",
    "product_version":"v1.0.0",
    "task_id":"TASK-000001",
    "repository":"quy7_roche/AI_Security_Gate",
    "branch":"main",
    "documents":["specs/architecture.md","specs/api-design.md","specs/data-model.md","specs/implementation-plan.md"],
    "gate1_report":"reports/.../Security-Review-Gate1-xxx.md",
    "threshold":0.78,
    "triggered_by":"api"
  }'
```

也支持：

```http
Authorization: Bearer <AI_SECURITY_GATE_API_KEY>
```

### 5.3 CI/CD Pipeline 调用

CI/CD Pipeline 使用同一个 `AI_SECURITY_GATE_API_KEY`。

Gate2 CI/CD 专用入口：

```text
POST /api/v1/ci/security-review/gate2/run
```

适合在构建、发布或合规检查流水线中直接触发 Gate2。

### 5.4 CLI 本地 Agent 调用

CLI 本地 Agent 面向 VS Code、本地终端和开发者脚本。

CLI 本地调用特性：

- 不需要 API Key
- 不创建 Review Task
- 不生成系统序列号
- 不写 `reports/` 或 `data/`
- 不需要 Approve
- 不自动触发 Gate2
- 只返回本地单次 Review 结果

Gate1：

```bash
python cli/security_gate_cli.py gate1 run \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md
```

Gate2：

```bash
python cli/security_gate_cli.py gate2 run \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md
```

Gate2 可选传入本地 Gate1 report：

```bash
python cli/security_gate_cli.py gate2 run \
  --docs specs/architecture.md specs/api-design.md \
  --gate1-report reports/local-gate1.md
```

CLI 输出中会包含：

```json
{
  "execution_mode": "local_cli_agent",
  "persistence": "none",
  "approval_required": false
}
```

---

## 6. API 文档服务

API 文档默认可通过独立端口访问：

```text
http://localhost:18081/docs
```

如果使用手动 `podman run` 或 `docker run`，需要映射：

```bash
-p 18081:8000
```

---

## 7. 测试

```bash
pytest -q
```

---

## 8. 安全说明

- 不要把 `.env` 提交到 Git。
- 不要在 UI 中展示或保存 `AI_SECURITY_GATE_API_KEY`。
- 外部 API 和 CI/CD 共享 `AI_SECURITY_GATE_API_KEY`。
- CLI 本地 Agent 不需要 API Key，也不走平台审批和报告持久化流程。
- LLM 不能自动 Approve、修改金标准知识库或降低匹配阈值。
