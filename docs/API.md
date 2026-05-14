# API Reference

默认服务地址：`http://localhost:8000`。Docker/Podman 默认宿主机端口为 `18080`，即 `http://localhost:18080`。

## Core Model: AI Gate Task

当前版本采用 Task / Activity 模型：

```text
Product Name + Product Version = AI Gate Task
Gate1 run = Task Activity
Gate2 run = Task Activity
Report edit / approve = Review activity audit event
```

默认 task id：

```text
task-{product_name_slug}-{product_version_slug}
```

每次运行 Gate1/Gate2 都会创建独立 activity/work order，并保存独立报告文件，历史不会被覆盖。

## Local Persistence

Task metadata：

```text
data/tasks/{product_name_slug}/{product_version_slug}/{task_id}.json
```

Activity / work order metadata：

```text
data/work_orders/{product_name_slug}/{product_version_slug}/{task_id}/{activity_id}.json
```

Reports：

```text
reports/{product_name_slug}/{product_version_slug}/{task_id}/{activity_id}/Security-Review-*.md
```

## Health / Dashboard / Catalog

```http
GET /api/v1/health
GET /api/v1/dashboard/stats
GET /api/v1/catalog
```

`/catalog` 用于 UI 下拉框，返回产品、版本、Task 列表。

## Gate1 Review Activity

```http
POST /api/v1/security-review/gate1/run
Content-Type: application/json
```

请求示例：

```json
{
  "project_id": "demo",
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
  "task_id": "task-demo-security-gate-product-v1.0.0",
  "task_name": "Demo Security Gate Product v1.0.0 AI Gate Task",
  "repository": "quy7_roche/AI_Security_Gate",
  "branch": "main",
  "documents": [
    "specs/product-requirements.md",
    "specs/user-stories.md",
    "specs/business-flow.md"
  ],
  "threshold": 0.78,
  "triggered_by": "ui"
}
```

响应包含：

```json
{
  "task_id": "task-demo-security-gate-product-v1.0.0",
  "work_order_id": "act-task-demo-security-gate-product-v1.0.0-gate1-...",
  "activity_id": "act-task-demo-security-gate-product-v1.0.0-gate1-...",
  "review_id": "gate1-review-...",
  "report_url": "/api/v1/reports/gate1-review-...",
  "report_download_url": "/api/v1/reports/gate1-review-.../download",
  "task_url": "/api/v1/tasks/task-demo-security-gate-product-v1.0.0"
}
```

## Gate2 Review Activity

```http
POST /api/v1/security-review/gate2/run
Content-Type: application/json
```

如果 `gate1_report` 为空，系统会自动查找同一 `product_name + product_version + task_id` 下最新 Gate1 报告。

请求示例：

```json
{
  "project_id": "demo",
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
  "task_id": "task-demo-security-gate-product-v1.0.0",
  "repository": "quy7_roche/AI_Security_Gate",
  "branch": "main",
  "documents": [
    "specs/architecture.md",
    "specs/api-design.md",
    "specs/data-model.md",
    "specs/implementation-plan.md"
  ],
  "gate1_report": null,
  "threshold": 0.78,
  "triggered_by": "ui"
}
```

## Task APIs

```http
GET /api/v1/tasks
GET /api/v1/tasks?product_name=Demo%20Security%20Gate%20Product
GET /api/v1/tasks?product_name=Demo%20Security%20Gate%20Product&product_version=v1.0.0
GET /api/v1/tasks/{task_id}
```

## Activity / Work Order APIs

```http
GET /api/v1/work-orders
GET /api/v1/work-orders?task_id=task-demo-security-gate-product-v1.0.0
GET /api/v1/work-orders?product_name=Demo%20Security%20Gate%20Product&product_version=v1.0.0&task_id=task-demo-security-gate-product-v1.0.0
GET /api/v1/work-orders/{work_order_id}
```

## Report APIs

```http
GET /api/v1/reports/{review_id}
GET /api/v1/reports/{review_id}/download
PUT /api/v1/reports/{review_id}
POST /api/v1/reports/{review_id}/approve
```

`GET /api/v1/reports/{review_id}` 返回 Markdown 文本，用于浏览器查看。

`GET /api/v1/reports/{review_id}/download` 以 Markdown 文件方式下载报告。

`PUT /api/v1/reports/{review_id}` 示例：

```json
{
  "content": "# Security Review Gate1 Report\n...",
  "reviewer": "security.reviewer@example.com",
  "comment": "Manual update"
}
```

`POST /api/v1/reports/{review_id}/approve` 示例：

```json
{
  "reviewer": "security.reviewer@example.com",
  "comment": "Approved"
}
```

## Knowledge Base APIs

```http
GET /api/v1/knowledge-base/{gate}
PUT /api/v1/knowledge-base/{gate}
GET /api/v1/knowledge-base/{gate}/history
```

其中 `{gate}` 为 `gate1` 或 `gate2`。

知识库更新只能由人工 UI/API 调用，评审引擎不会修改知识库。每次人工修改都会保存一条历史记录到：

```text
data/knowledge_base_history/{gate}/
```

知识库更新示例：

```json
{
  "version": "1.0.1",
  "updated_by": "security.admin@example.com",
  "change_reason": "Manual update from UI/API",
  "content": {
    "schema_version": "1.0.0",
    "knowledge_base_version": "1.0.1",
    "gate": "Gate1",
    "llm_editable": false,
    "matching_policy": {},
    "scenarios": []
  }
}
```
