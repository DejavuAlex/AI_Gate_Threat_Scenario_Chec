# AI Security Gate

AI Security Gate 是一个面向 Speckit / 文档驱动研发流程的自动化安全评审与威胁建模系统。系统通过 Gate1 和 Gate2 两个阶段，对业务需求、架构设计、API 设计、数据模型和实现计划进行安全风险识别，并生成可人工审阅、修改和审批的 Markdown 安全评审报告。

当前仓库已经实现可运行 MVP，并支持 OpenAI-compatible LLM Gateway，例如企业 Azure OpenAI / OpenAI API Gateway。

---

## 1. 核心能力

### Gate1：业务需求安全评审

Gate1 面向业务需求阶段，读取如下类型文档：

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
- 输出 `reports/Security-Review-Gate1.md`
- 支持人工编辑和 Approve

### Gate2：架构 / API / 技术需求安全评审

Gate2 面向架构和实现设计阶段，读取如下类型文档：

```text
specs/architecture.md
specs/api-design.md
specs/data-model.md
specs/implementation-plan.md
```

Gate2 会：

- 读取 Gate2 金标准知识库
- 匹配技术安全风险场景
- 读取 Gate1 报告
- 验证 Gate1 安全控制措施是否落实到 Gate2 文档中
- 输出未落实项和优化建议
- 生成 `reports/Security-Review-Gate2.md`

### LLM 集成

系统支持 OpenAI-compatible LLM Gateway：

- 通过环境变量配置
- 不在仓库中保存 API Key
- LLM 仅作为辅助匹配、证据提取和控制措施优化层
- LLM 调用失败时自动 fallback 到确定性匹配引擎
- LLM 不允许修改金标准知识库
- LLM 不允许降低阈值或强行匹配
- LLM 不允许自动 Approve 报告

---

## 2. 当前项目结构

```text
AI_Security_Gate/
  backend/
    __init__.py
    app/
      __init__.py
      main.py                    FastAPI 应用入口
      api.py                     REST API 路由
      config.py                  全局配置、路径、LLM 环境变量
      schemas.py                 Pydantic 请求/响应模型
      static/
        index.html               Web UI 页面
      services/
        __init__.py
        documents.py             读取 Speckit / Markdown 文档
        knowledge_base.py        金标准知识库读取和人工保存
        matching.py              确定性匹配评分引擎
        llm_client.py            OpenAI-compatible LLM 客户端
        llm_matching.py          LLM 辅助匹配逻辑
        gate2_verifier.py        Gate2 验证 Gate1 控制措施
        report_generator.py      Markdown 报告生成器
        review.py                Gate1/Gate2 Review 编排服务

  cli/
    security_gate_cli.py         本地 CLI 入口

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

  reports/
    .gitkeep                     运行后生成 Security-Review-Gate1.md / Gate2.md

  data/
    .gitkeep                     运行后生成 review metadata

  docs/
    API.md                       API 文档
    ARCHITECTURE.md              架构说明
    DEVELOPMENT.md               开发说明
    LLM.md                       LLM 集成说明

  tests/
    __init__.py
    test_api.py
    test_knowledge_base.py
    test_matching.py
    test_llm_config.py

  Dockerfile
  docker-compose.yml
  requirements.txt
  requirements-dev.txt
  pyproject.toml
  .env.example
  .gitignore
```

---

## 3. 从 0 开始安装

### 3.1 环境要求

推荐环境：

```text
Python: 3.10+
推荐 Python: 3.11
Git: 最新版
Docker: 可选
浏览器: Chrome / Edge / Firefox
```

检查 Python：

```bash
python --version
```

或：

```bash
python3 --version
```

检查 Git：

```bash
git --version
```

### 3.2 克隆仓库

```bash
git clone https://github.com/quy7_roche/AI_Security_Gate.git
cd AI_Security_Gate
```

### 3.3 创建虚拟环境

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

### 3.4 安装依赖

```bash
pip install -r requirements.txt
```

如果需要运行测试：

```bash
pip install -r requirements-dev.txt
```

---

## 4. 启动服务

### 4.1 本地启动

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问：

```text
http://localhost:8000
```

Swagger API 文档：

```text
http://localhost:8000/docs
```

健康检查：

```bash
curl http://localhost:8000/api/v1/health
```

预期返回：

```json
{
  "status": "ok"
}
```

### 4.2 Docker 启动

```bash
docker compose up --build
```

后台启动：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

---

## 5. LLM 配置

项目支持 OpenAI-compatible API Gateway。请勿将真实 API Key 提交到 GitHub。

### 5.1 创建本地 `.env`

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
AI_LLM_ENABLED=true
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-2025-08-07
OPENAI_BASE_URL=https://eu.aigw.galileo.roche.com/v1
OPENAI_API_KEY=<your-secret-key>
LLM_MATCHING_TEMPERATURE=0
LLM_MATCHING_TIMEOUT_SECONDS=60
```

如果不希望启用 LLM，可设置：

```bash
AI_LLM_ENABLED=false
```

### 5.2 LLM 行为边界

LLM 可以：

- 辅助理解业务需求
- 辅助匹配知识库场景
- 提取匹配证据
- 优化安全控制措施表达
- 辅助 Gate2 验证 Gate1 控制措施落实情况

LLM 不可以：

- 修改金标准知识库
- 新增或虚构知识库场景
- 降低匹配阈值
- 强行匹配低置信度场景
- 自动 Approve 报告
- 自动修改原始需求文档

### 5.3 Fallback 机制

如果满足以下任一条件：

- `AI_LLM_ENABLED=false`
- API Key 未配置
- LLM Gateway 不可用
- LLM 返回非 JSON
- LLM 调用超时或失败

系统会自动回退到确定性匹配引擎，不影响 Gate1/Gate2 基础评审能力。

---

## 6. Web UI 使用手册

启动服务后访问：

```text
http://localhost:8000
```

页面包含：

```text
Dashboard
Gate1 Review
Gate2 Review
Report Center / Approval
Knowledge Base Management
```

### 6.1 检查服务状态

在 Dashboard 中点击：

```text
检查服务状态
```

正常时返回：

```json
{
  "status": "ok"
}
```

### 6.2 运行 Gate1 Review

默认文档：

```text
specs/product-requirements.md
specs/user-stories.md
specs/business-flow.md
```

操作：

1. 打开首页。
2. 找到 `Gate1 Review`。
3. 确认文档路径和阈值。
4. 点击 `Run Gate1 Review`。
5. 系统生成 `reports/Security-Review-Gate1.md`。

返回中会包含：

```text
review_id
matched
matched_scenarios
report_path
approval_status
llm_enabled
llm_error
```

### 6.3 查看和编辑 Gate1 报告

1. Gate1 运行后，`review_id` 会自动填入 Report Center。
2. 点击 `View Report`。
3. 在文本框中查看 Markdown 报告。
4. 如需修改，直接编辑文本框内容。
5. 点击 `Save Edited Report`。

### 6.4 Approve Gate1 报告

1. 填写 Reviewer。
2. 点击 `Approve`。
3. 系统会把 `approval_status` 更新为 `approved`。
4. 审计记录写入 `data/reviews/{review_id}.json`。

### 6.5 运行 Gate2 Review

运行 Gate2 前建议先运行 Gate1，确保存在：

```text
reports/Security-Review-Gate1.md
```

默认 Gate2 文档：

```text
specs/architecture.md
specs/api-design.md
specs/data-model.md
specs/implementation-plan.md
```

操作：

1. 找到 `Gate2 Review`。
2. 确认 Gate1 Report 路径。
3. 点击 `Run Gate2 Review`。
4. 系统生成 `reports/Security-Review-Gate2.md`。

Gate2 报告会包含：

- Gate2 匹配到的威胁场景
- 场景评分
- 安全控制要求
- Gate1 控制措施落实检查
- 未落实项
- 技术文档优化建议

### 6.6 管理知识库

在 `Knowledge Base Management` 区域：

1. 选择 `gate1` 或 `gate2`。
2. 点击 `Load KB`。
3. 查看或人工修改 JSON。
4. 填写 Version、Updated By、Change Reason。
5. 点击 `Manual Save KB`。

注意：当前 MVP 没有登录鉴权，生产环境必须限制该功能只能 Security Admin 使用。

---

## 7. CLI 使用手册

CLI 文件：

```text
cli/security_gate_cli.py
```

### 7.1 运行 Gate1

```bash
python cli/security_gate_cli.py gate1 run \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md \
  --threshold 0.78
```

带 repo 和 branch：

```bash
python cli/security_gate_cli.py gate1 run \
  --repo quy7_roche/AI_Security_Gate \
  --branch main \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md \
  --threshold 0.78
```

### 7.2 运行 Gate2

```bash
python cli/security_gate_cli.py gate2 run \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md \
  --gate1-report reports/Security-Review-Gate1.md \
  --threshold 0.78
```

---

## 8. API 使用手册

基础地址：

```text
http://localhost:8000
```

### 8.1 Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### 8.2 触发 Gate1

```bash
curl -X POST http://localhost:8000/api/v1/security-review/gate1/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "repository": "quy7_roche/AI_Security_Gate",
    "branch": "main",
    "documents": [
      "specs/product-requirements.md",
      "specs/user-stories.md",
      "specs/business-flow.md"
    ],
    "knowledge_base_version": "latest",
    "threshold": 0.78,
    "triggered_by": "api"
  }'
```

### 8.3 触发 Gate2

```bash
curl -X POST http://localhost:8000/api/v1/security-review/gate2/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "repository": "quy7_roche/AI_Security_Gate",
    "branch": "main",
    "documents": [
      "specs/architecture.md",
      "specs/api-design.md",
      "specs/data-model.md",
      "specs/implementation-plan.md"
    ],
    "gate1_report": "reports/Security-Review-Gate1.md",
    "knowledge_base_version": "latest",
    "threshold": 0.78,
    "triggered_by": "api"
  }'
```

### 8.4 查询 Review 详情

Gate1：

```bash
curl http://localhost:8000/api/v1/security-review/gate1/{review_id}
```

Gate2：

```bash
curl http://localhost:8000/api/v1/security-review/gate2/{review_id}
```

### 8.5 获取报告

```bash
curl http://localhost:8000/api/v1/reports/{review_id}
```

### 8.6 修改报告

```bash
curl -X PUT http://localhost:8000/api/v1/reports/{review_id} \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Security Review Report\n\n人工修改后的内容",
    "reviewer": "security.reviewer@example.com",
    "comment": "Manual update"
  }'
```

### 8.7 Approve 报告

```bash
curl -X POST http://localhost:8000/api/v1/reports/{review_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer": "security.reviewer@example.com",
    "comment": "Approved"
  }'
```

### 8.8 获取知识库

```bash
curl http://localhost:8000/api/v1/knowledge-base/gate1
curl http://localhost:8000/api/v1/knowledge-base/gate2
```

---

## 9. 报告说明

### Gate1 报告

输出文件：

```text
reports/Security-Review-Gate1.md
```

主要章节：

```text
1. Review Metadata
2. Input Documents
3. Matching Result
4. Final Security Control Requirements
5. Human Review
```

### Gate2 报告

输出文件：

```text
reports/Security-Review-Gate2.md
```

主要章节：

```text
1. Review Metadata
2. Input Documents
3. Gate2 Knowledge Base Matching Result
4. Gate1 Security Control Verification
5. Non-compliance Findings
6. Optimized Gate2 Requirement Updates
7. Final Security Control Requirements
8. Conclusion
```

---

## 10. 金标准知识库说明

Gate1：

```text
knowledge_base/gate1/default-gate1-knowledge-base.json
```

Gate2：

```text
knowledge_base/gate2/default-gate2-knowledge-base.json
```

每个知识库包含：

```text
schema_version
knowledge_base_version
gate
name
description
llm_editable
matching_policy
scenarios
```

重要约束：

```text
llm_editable=false
```

这表示：

- LLM 不允许修改知识库
- 评审引擎只读取知识库
- 只有人工 UI/API 流程可以更新知识库

---

## 11. 测试手册

安装测试依赖：

```bash
pip install -r requirements-dev.txt
```

运行测试：

```bash
python -m pytest -q
```

当前测试覆盖：

- API health check
- Gate1/Gate2 知识库 JSON 有效性
- Gate1/Gate2 知识库场景数量
- `llm_editable=false`
- 匹配引擎正向匹配
- 负向证据不强行匹配
- LLM client 安全初始化

---

## 12. CI/CD 集成建议

由于企业权限限制，`.github/workflows/*` 可能需要具备 workflow 权限的账号手动添加。

### 12.1 CLI 集成方式

在任意 CI 中执行：

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest -q

python cli/security_gate_cli.py gate1 run \
  --repo "$GITHUB_REPOSITORY" \
  --branch "$GITHUB_HEAD_REF" \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md \
  --threshold 0.78

python cli/security_gate_cli.py gate2 run \
  --repo "$GITHUB_REPOSITORY" \
  --branch "$GITHUB_HEAD_REF" \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md \
  --gate1-report reports/Security-Review-Gate1.md \
  --threshold 0.78
```

### 12.2 API 集成方式

如果将服务部署为内部服务，例如：

```text
https://security-gate.example.com
```

CI 可调用：

```bash
curl -X POST https://security-gate.example.com/api/v1/security-review/gate1/run \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "demo",
    "repository": "quy7_roche/AI_Security_Gate",
    "branch": "main",
    "documents": ["specs/product-requirements.md", "specs/user-stories.md", "specs/business-flow.md"],
    "threshold": 0.78,
    "triggered_by": "ci"
  }'
```

---

## 13. 常见问题

### 13.1 服务启动后页面打不开

确认服务是否运行：

```bash
curl http://localhost:8000/api/v1/health
```

重新启动：

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 13.2 CLI 报模块找不到

确认在项目根目录运行：

```bash
pwd
ls
```

应看到：

```text
backend
cli
knowledge_base
```

### 13.3 Gate1 未匹配场景

这是正常行为。系统低于阈值不会强行匹配，会返回：

```text
未匹配上任何威胁场景，本次安全评估确认无安全风险。
```

建议检查：

- 文档路径是否正确
- 文档内容是否包含相关业务场景
- 阈值是否过高
- 是否存在 negative indicators

### 13.4 Gate2 找不到 Gate1 报告

先运行 Gate1：

```bash
python cli/security_gate_cli.py gate1 run \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md
```

确认存在：

```text
reports/Security-Review-Gate1.md
```

再运行 Gate2。

### 13.5 LLM 未启用

检查 `.env`：

```bash
AI_LLM_ENABLED=true
OPENAI_API_KEY=<your-secret-key>
OPENAI_BASE_URL=https://eu.aigw.galileo.roche.com/v1
OPENAI_MODEL=gpt-5-2025-08-07
```

如果仍失败，查看 review JSON 中的：

```text
llm_enabled
llm_error
```

### 13.6 Docker 启动后 LLM 不生效

确认当前目录存在 `.env`，并且 `docker-compose.yml` 中包含：

```yaml
env_file:
  - .env
```

重新构建：

```bash
docker compose down
docker compose up --build
```

---

## 14. 当前 MVP 的边界

当前版本已经具备完整演示和 PoC 能力，但不是生产级安全平台。生产化前建议补充：

- 用户登录
- OAuth2 / SSO
- RBAC
- 知识库管理权限控制
- PostgreSQL / MySQL 持久化
- 完整审计日志
- PR comment bot
- GitHub Actions workflow
- LLM 输出 JSON Schema 强校验
- Prompt injection 更强防护
- Gate2 自动生成文档 patch 并人工确认

---

## 15. 推荐使用流程

```text
1. 开发人员编写 specs/product-requirements.md、user-stories.md、business-flow.md
2. 运行 Gate1
3. 生成 Security-Review-Gate1.md
4. 安全 reviewer 人工修改并 Approve
5. 开发人员编写 architecture.md、api-design.md、data-model.md、implementation-plan.md
6. 运行 Gate2
7. Gate2 验证 Gate1 控制措施是否落实
8. 根据 Gate2 未落实项更新技术设计文档
9. 再次运行 Gate2，直到无关键未落实项
```

---

## 16. 快速命令汇总

安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

启动：

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

启用 LLM：

```bash
cp .env.example .env
# 编辑 .env，填写 OPENAI_API_KEY
```

运行 Gate1：

```bash
python cli/security_gate_cli.py gate1 run \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md
```

运行 Gate2：

```bash
python cli/security_gate_cli.py gate2 run \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md \
  --gate1-report reports/Security-Review-Gate1.md
```

运行测试：

```bash
python -m pytest -q
```

Docker 启动：

```bash
docker compose up --build
```
