# Enterprise AI Knowledge Assistant Architecture

## Prompt boundary

G1-AI-001 uses an instruction hierarchy, system prompt isolation, a prompt injection detector, a context redaction pipeline, and an LLM input policy before model invocation.

## Retrieval boundary

G1-AI-002 uses an embedding ingestion pipeline with chunk ACL metadata. Every vector database tenant filter is mandatory, responses include a retrieval citation, and deletion uses vector tombstone deletion.

## Tool boundary

G1-AI-003 routes actions through a tool allowlist gateway. JSON Schema tool arguments, a human approval checkpoint, an agent execution sandbox, and a scoped tool token are mandatory.
