# Architecture

## Overview

AI Security Gate 是一个 Speckit 文档驱动的 DevSecOps 安全门系统，包含 Gate1 和 Gate2 两个阶段。

```text
UI / CLI / CI
    |
    v
FastAPI Backend
    |
    +-- Document Reader
    +-- Knowledge Base Service
    +-- Matching Engine
    +-- Gate2 Verifier
    +-- Report Generator
    |
    v
reports/ + data/ + knowledge_base/
```

## Gate1

Gate1 面向业务需求文档，例如：

- `specs/product-requirements.md`
- `specs/user-stories.md`
- `specs/business-flow.md`

核心输出：

- `reports/Security-Review-Gate1.md`

## Gate2

Gate2 面向架构、API、数据模型和实现计划文档，例如：

- `specs/architecture.md`
- `specs/api-design.md`
- `specs/data-model.md`
- `specs/implementation-plan.md`

Gate2 会读取 Gate1 报告并验证安全控制措施是否在技术文档中落实。

核心输出：

- `reports/Security-Review-Gate2.md`

## Matching Engine

当前 MVP 使用确定性评分机制，便于审计和测试：

- semantic token overlap
- keyword match
- business / architecture context
- negative evidence adjustment
- confidence score

低于阈值时不会强行匹配。

## Knowledge Base Guardrails

- `llm_editable=false`
- 评审引擎只调用 `KnowledgeBaseService.load`
- 只有 UI/API 人工路径可调用 `save_manual_update`
- 每次人工修改会写入 audit metadata

## Local Runtime

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker Runtime

```bash
docker compose up --build
```
