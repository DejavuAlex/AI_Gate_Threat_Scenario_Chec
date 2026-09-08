# Enterprise AI Knowledge Assistant API Design

## Conversation API

`POST /v1/assistant/messages` separates system instructions, retrieved context, and user content. Input and output policies reject secret extraction and cross-tenant content.

## Retrieval API

`POST /v1/retrieval/query` derives mandatory tenant and ACL filters from the authenticated principal; callers cannot override them. Results include document and chunk citations.

## Tool gateway API

`POST /v1/agent/tools/{toolId}/execute` accepts allowlisted tools and JSON Schema-valid arguments. High-impact tools require a pending approval identifier bound to the requester and intent.
