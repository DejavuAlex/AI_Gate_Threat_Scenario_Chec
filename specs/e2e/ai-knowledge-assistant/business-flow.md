# Enterprise AI Knowledge Assistant Business Flow

1. The user submits AI对话输入 to the assistant.
2. The policy service classifies and redacts the prompt.
3. The retrieval service performs 检索增强生成 over authorized tenant documents.
4. The model may propose an AI代理调用工具 operation with structured arguments.
5. A policy decision and human confirmation precede the external business action.
6. The platform records retrieval provenance, approval, tool execution, and result.
