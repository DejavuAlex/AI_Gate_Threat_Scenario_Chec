# AI Security Gate

AI 驱动的自动化安全评审与威胁建模系统，面向 Speckit 文档驱动的 DevSecOps 工作流。

## 功能

- Gate1：业务需求安全评审，基于业务层级文档匹配金标准威胁场景并生成 `Security-Review-Gate1.md`
- Gate2：架构 / 代码级需求安全评审，匹配技术威胁场景并验证 Gate1 安全控制措施落地情况，生成 `Security-Review-Gate2.md`
- 金标准知识库：JSON 文件，LLM/匹配引擎只读，必须通过 UI/API 人工修改
- UI：手动触发 Gate1/Gate2、配置阈值、查看/编辑/Approve 报告、管理知识库
- API：可供 CI/CD pipeline 调用
- CLI：本地或 VS Code agent 可调用

## 快速启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

打开：<http://localhost:8000>

## API 示例

```bash
curl -X POST http://localhost:8000/api/v1/security-review/gate1/run \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id":"demo",
    "repository":"quy7_roche/AI_Security_Gate",
    "branch":"main",
    "documents":["specs/product-requirements.md","specs/user-stories.md","specs/business-flow.md"],
    "threshold":0.78,
    "triggered_by":"local"
  }'
```

```bash
curl -X POST http://localhost:8000/api/v1/security-review/gate2/run \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id":"demo",
    "repository":"quy7_roche/AI_Security_Gate",
    "branch":"main",
    "documents":["specs/architecture.md","specs/api-design.md","specs/data-model.md","specs/implementation-plan.md"],
    "gate1_report":"reports/Security-Review-Gate1.md",
    "threshold":0.78,
    "triggered_by":"local"
  }'
```

## CLI 示例

```bash
python cli/security_gate_cli.py gate1 run --docs specs/product-requirements.md specs/user-stories.md --threshold 0.78
python cli/security_gate_cli.py gate2 run --docs specs/architecture.md specs/api-design.md --gate1-report reports/Security-Review-Gate1.md
```

## 项目结构

```text
backend/app/              FastAPI 后端、匹配引擎、报告生成器
backend/app/static/       Web UI
knowledge_base/           Gate1/Gate2 金标准知识库
reports/                  生成的安全评审报告
data/                     Review 任务、审批和审计数据
specs/                    Speckit 示例文档
cli/                      本地命令行入口
.github/workflows/        CI/CD 调用示例
```

## 安全约束

- 知识库文件 `llm_editable=false`，评审引擎不会自动修改知识库
- 低于阈值不强行匹配，返回“未匹配上任何威胁场景，本次安全评估确认无安全风险。”
- Gate1 报告支持人工修改和 Approve
- 所有 API 生成结果写入本地 `data/` 与 `reports/`，便于审计
