# API Reference

默认服务地址：`http://localhost:8000`。

## Health

```http
GET /api/v1/health
```

## Gate1 Review

```http
POST /api/v1/security-review/gate1/run
Content-Type: application/json
```

请求示例：

```json
{
  "project_id": "demo",
  "repository": "quy7_roche/AI_Security_Gate",
  "branch": "main",
  "documents": [
    "specs/product-requirements.md",
    "specs/user-stories.md",
    "specs/business-flow.md"
  ],
  "threshold": 0.78,
  "triggered_by": "ci"
}
```

## Gate2 Review

```http
POST /api/v1/security-review/gate2/run
Content-Type: application/json
```

请求示例：

```json
{
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
  "threshold": 0.78,
  "triggered_by": "ci"
}
```

## Report APIs

```http
GET /api/v1/reports/{review_id}
PUT /api/v1/reports/{review_id}
POST /api/v1/reports/{review_id}/approve
```

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
```

其中 `{gate}` 为 `gate1` 或 `gate2`。

知识库更新只能由人工 UI/API 调用，评审引擎不会修改知识库。
