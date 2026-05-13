# Data Model

## security_review_task

- id
- project_id
- gate
- repository
- branch
- status
- threshold
- knowledge_base_version
- triggered_by
- created_at
- completed_at

## matched_scenario

- id
- review_id
- scenario_id
- scenario_name
- final_score
- risk_level
- evidence_json
- score_breakdown_json

## security_review_report

- id
- review_id
- report_type
- report_path
- content
- approval_status
- approved_by
- approved_at
- created_at
- updated_at

## knowledge_base_version

- id
- gate
- version
- content_json
- created_by
- change_reason
- created_at
