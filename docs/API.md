# API Reference

默认服务地址：`http://localhost:8000`。Docker/Podman 默认宿主机端口为 `18080`，即 `http://localhost:18080`。

## Review Flow

一次安全评审工单以系统内部序列号标识：

```text
task_serial_no: 1, 2, 3...
task_code: TASK-000001
```

默认流程：

```text
1. 下发 Gate1 review task
2. 人工 approve Gate1 report
3. 如果 Gate1 无安全风险：task 结束，final_result = no_security_risk
4. 如果 Gate1 有安全风险：自动触发 Gate2，Gate2 继承 Gate1 的产品、版本、task、repo、branch、threshold 等参数
5. Gate2 生成独立 report，人工 approve Gate2 后流程完成
6. 可通过 task final report API 查看一次工单的最终汇总
```

Task / activity/report 持久化：

```text
data/task_sequence.json
data/tasks/{product}/{version}/{task_id}.json
data/work_orders/{product}/{version}/{task_id}/{activity_id}.json
reports/{product}/{version}/{task_id}/{activity_id}/Security-Review-*.md
```

## Dashboard / Catalog

```http
GET /api/v1/health
GET /api/v1/dashboard/stats
GET /api/v1/catalog
```

## Gate1 API

```http
POST /api/v1/security-review/gate1/run
Content-Type: application/json
```

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
  "gate2_documents": [
    "specs/architecture.md",
    "specs/api-design.md",
    "specs/data-model.md",
    "specs/implementation-plan.md"
  ],
  "threshold": 0.78,
  "triggered_by": "ci",
  "auto_run_gate2_on_gate1_approval": true
}
```

## Gate1 Approve API

```http
POST /api/v1/security-review/gate1/{review_id}/approve
POST /api/v1/reports/{review_id}/approve
Content-Type: application/json
```

```json
{
  "reviewer": "security.reviewer@example.com",
  "comment": "Approved"
}
```

响应中如果 `auto_gate2_triggered=true`，表示 Gate1 有风险且系统已经自动运行 Gate2：

```json
{
  "auto_gate2_triggered": true,
  "auto_gate2_result": {
    "review_id": "gate2-review-...",
    "report_url": "/api/v1/reports/gate2-review-...",
    "report_download_url": "/api/v1/reports/gate2-review-.../download"
  }
}
```

## Gate2 Direct API

Gate2 仍支持直接调用，适用于 UI、API 和外部服务：

```http
POST /api/v1/security-review/gate2/run
Content-Type: application/json
```

CI/CD 友好别名：

```http
POST /api/v1/ci/security-review/gate2/run
Content-Type: application/json
```

```json
{
  "project_id": "demo",
  "product_name": "Demo Security Gate Product",
  "product_version": "v1.0.0",
  "task_id": "TASK-000001",
  "repository": "quy7_roche/AI_Security_Gate",
  "branch": "main",
  "documents": [
    "specs/architecture.md",
    "specs/api-design.md",
    "specs/data-model.md",
    "specs/implementation-plan.md"
  ],
  "gate1_report": "reports/.../Security-Review-Gate1-xxx.md",
  "threshold": 0.78,
  "triggered_by": "ci-cd"
}
```

If `gate1_report` is omitted, the service tries to use the latest Gate1 report under the same task.

## Task APIs

```http
GET /api/v1/tasks
GET /api/v1/tasks?product_name=Demo%20Security%20Gate%20Product
GET /api/v1/tasks?product_name=Demo%20Security%20Gate%20Product&product_version=v1.0.0
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/final-report
GET /api/v1/tasks/{task_id}/final-report/download
```

Task list items include:

```text
task_serial_no
task_code
task_name
product_name
product_version
flow_status
final_result
triggered_by
latest_gate1_review_id
latest_gate1_report_url
latest_gate1_download_url
latest_gate2_review_id
latest_gate2_report_url
latest_gate2_download_url
approval
auto_gate2
final_report_url
final_report_download_url
```

The final task report is an on-demand Markdown summary that includes:

```text
Task identity
Workflow status
Gate1/Gate2 approval summary
Generated report links
Gate run timeline
References to detailed story-level scoring reports
```

## Work Order / Activity APIs

```http
GET /api/v1/work-orders
GET /api/v1/work-orders?task_id=TASK-000001
GET /api/v1/work-orders/{work_order_id}
```

## Report APIs

```http
GET /api/v1/reports/{review_id}
GET /api/v1/reports/{review_id}/download
PUT /api/v1/reports/{review_id}
POST /api/v1/reports/{review_id}/approve
POST /api/v1/security-review/gate2/{review_id}/approve
```

## CLI Examples

Gate1 with Gate2 documents for auto-run:

```bash
python cli/security_gate_cli.py gate1 run \
  --product-name "Demo Security Gate Product" \
  --product-version "v1.0.0" \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md \
  --gate2-docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md
```

Approve Gate1 and auto-run Gate2 if risk exists:

```bash
python cli/security_gate_cli.py approve \
  --review-id gate1-review-xxx \
  --reviewer security.reviewer@example.com \
  --comment "Approved"
```

Direct Gate2:

```bash
python cli/security_gate_cli.py gate2 run \
  --product-name "Demo Security Gate Product" \
  --product-version "v1.0.0" \
  --task-id TASK-000001 \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md \
  --gate1-report reports/.../Security-Review-Gate1-xxx.md \
  --triggered-by ci
```

Final task report reference:

```bash
python cli/security_gate_cli.py final-report --task-id TASK-000001
```

## CI/CD curl Example

```bash
curl -X POST "http://localhost:18080/api/v1/ci/security-review/gate2/run" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id":"demo",
    "product_name":"Demo Security Gate Product",
    "product_version":"v1.0.0",
    "task_id":"TASK-000001",
    "repository":"quy7_roche/AI_Security_Gate",
    "branch":"main",
    "documents":["specs/architecture.md","specs/api-design.md","specs/data-model.md","specs/implementation-plan.md"],
    "threshold":0.78,
    "triggered_by":"ci-cd"
  }'
```

## Final Report curl Example

```bash
curl "http://localhost:18080/api/v1/tasks/TASK-000001/final-report"

curl -OJ "http://localhost:18080/api/v1/tasks/TASK-000001/final-report/download"
```

## Knowledge Base APIs

```http
GET /api/v1/knowledge-base/{gate}
PUT /api/v1/knowledge-base/{gate}
GET /api/v1/knowledge-base/{gate}/history
POST /api/v1/knowledge-base/{gate}/assistant/propose
```

每次人工更新知识库都会保存历史记录：

```text
data/knowledge_base_history/{gate}/
```

### 金标准场景对话助手

助手要求 LLM 使用自身安全知识独立生成一条可编辑的新候选。现有知识库的名称、版本、示例和场景内容均不会发送给 LLM；它们仅在服务端用于字段校验和新 Scenario ID 防冲突。`S` 在知识库 JSON 中沿用现有字段名 `severity`。该接口只生成候选，不写文件；用户确认后仍需调用 `PUT /api/v1/knowledge-base/{gate}` 才会同步并生成变更记录。

```http
POST /api/v1/knowledge-base/gate1/assistant/propose
Content-Type: application/json

{
  "knowledge_base_id": "default",
  "message": "外部用户可以上传医学影像，并通过临时链接分享给医生",
  "conversation": [],
  "draft_scenario": null,
  "draft_action": null,
  "draft_matched_scenario_id": null
}
```

响应固定使用 `action: "add"`，不匹配或引用已有场景，并包含完整 `scenario` 候选和便于 UI 展示的风险摘要，其中 `risk_summary.S` 对应 `scenario.risk.severity`。
