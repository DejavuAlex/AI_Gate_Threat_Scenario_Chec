# Implementation Plan

## Phase 1

- Implement FastAPI backend.
- Implement Gate1/Gate2 knowledge base loading.
- Implement deterministic matching and scoring engine.
- Implement Markdown report generation.

## Phase 2

- Implement static Web UI.
- Implement report edit and approve workflow.
- Implement knowledge base manual management UI.

## Phase 3

- Implement CLI for local and VS Code agent workflows.
- Implement GitHub Actions examples for Gate1 and Gate2.

## Security Controls

- 文件上传场景：限制文件类型、校验 Magic Number、限制文件大小。
- API接口暴露：OAuth2.0 鉴权、RBAC 授权、Schema 校验、频率限制。
- 管理后台：强制 MFA、IP 白名单、登录失败锁定和操作审计。
- 配置文件管理：敏感配置通过环境变量或 Vault/KMS 注入。
