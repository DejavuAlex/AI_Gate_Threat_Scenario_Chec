# Architecture

## Overview

系统采用 FastAPI 后端和静态 Web UI 的轻量架构。后端提供 REST API 给 UI、CLI 和 CI/CD pipeline 调用。

## Components

- Web UI：触发 Gate1/Gate2 review、展示报告、人工 approve、管理知识库。
- API Service：提供 `/api/v1/security-review/gate1/run` 和 `/api/v1/security-review/gate2/run`。
- Matching Engine：基于关键词、语义 token、上下文和负面证据进行评分。
- Knowledge Base Service：读取 Gate1/Gate2 JSON 知识库。评审引擎只读，知识库修改只能通过人工 API/UI 完成。
- Report Generator：生成 Markdown 报告。

## Security Architecture

- 所有对外 API 均应接入 OAuth2.0 鉴权和细粒度 RBAC。
- 管理员后台必须强制 MFA，并限制访问来源 IP。
- 上传接口必须限制文件大小、文件类型，并校验 Magic Number。
- 敏感配置通过环境变量注入，不在代码仓库中硬编码密钥。
- 所有报告审批、知识库修改均记录审计日志。
