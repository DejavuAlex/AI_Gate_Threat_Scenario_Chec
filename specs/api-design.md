# API Design

## Gate1 Review

`POST /api/v1/security-review/gate1/run`

- Authentication: OAuth2.0 Bearer Token
- Authorization: Developer or Security Reviewer
- Rate Limit: token bucket per user and per repository
- Input Schema: project_id, repository, branch, documents, threshold

## Gate2 Review

`POST /api/v1/security-review/gate2/run`

- Authentication: OAuth2.0 Bearer Token
- Authorization: Developer or Security Reviewer
- Rate Limit: token bucket per user and per repository
- Input Schema: project_id, repository, branch, documents, gate1_report, threshold

## Reports

`GET /api/v1/reports/{review_id}`

`PUT /api/v1/reports/{review_id}`

`POST /api/v1/reports/{review_id}/approve`

## Knowledge Base

`GET /api/v1/knowledge-base/{gate}`

`PUT /api/v1/knowledge-base/{gate}`

- Authorization: Security Admin only
- Audit: every update must include updated_by and change_reason
