# Enterprise AI Knowledge Assistant Data Model

## VectorChunk

- tenant, document, and immutable chunk identifiers
- ACL metadata and source classification
- embedding model version
- source citation and deletion status

## AgentToolDecision

- user and tenant identifiers
- prompt and policy decision references
- allowlisted tool and validated argument digest
- human approver and approval timestamp
- scoped credential reference and execution result

Secrets and raw credentials are excluded from both records.
