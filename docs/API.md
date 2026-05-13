# API Reference

默认服务地址：`http://localhost:8000`。Docker/Podman 默认宿主机端口为 `18080`，即 `http://localhost:18080`。

## Health

```http
GET /api/v1/health
```

## Review Work Order Model

每次触发 Gate1/Gate2 都会创建一个独立评审工单，按产品名称和产品版本分类保存：

- `product_name`：产品名称
- `product_version`：产品版本
- `work_order_id`：系统生成的工单 ID
- `review_id`：系统生成的单次 review ID
- `report_url`：报告查看链接
- `report_download_url`：报告下载链接

工单元数据保存到：

```text
data/work_orders/{product_name_slug}/{product_version_slug}/{work_order_id}.json
```

报告保存到：

```text
reports/{product_name_slug}/{product_version_slug}/{work_order_id}/Security-Review-*.md
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
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
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

响应示例：

```json
{
  "work_order_id": "wo-demo-security-gate-product-v1.0.0-gate1-...",
  "review_id": "gate1-review-...",
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
  "gate": "gate1",
  "status": "completed",
  "matched": true,
  "report_path": "reports/demo-security-gate-product/v1.0.0/.../Security-Review-Gate1-....md",
  "report_url": "/api/v1/reports/gate1-review-...",
  "report_download_url": "/api/v1/reports/gate1-review-.../download",
  "work_order_url": "/api/v1/work-orders/wo-demo-security-gate-product-v1.0.0-gate1-..."
}
```

## Gate2 Review

```http
POST /api/v1/security-review/gate2/run
Content-Type: application/json
```

如果 `gate1_report` 为空，系统会自动查找同一 `product_name + product_version` 下最新 Gate1 报告。

请求示例：

```json
{
  "project_id": "demo",
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
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
  "triggered_by": "ci"
}
```

## Work Order APIs

```http
GET /api/v1/work-orders
GET /api/v1/work-orders?product_name=Demo%20Security%20Gate%20Product
GET /api/v1/work-orders?product_name=Demo%20Security%20Gate%20Product&product_version=v1.0.0
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
