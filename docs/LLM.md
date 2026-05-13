# LLM Integration Guide

本项目支持通过 OpenAI-compatible API 接入 Azure OpenAI / 企业 AI Gateway。

## 安全原则

不要将真实 API key 提交到 GitHub。请使用：

- 本地 `.env`
- GitHub Actions Secrets
- Kubernetes Secret
- Vault / KMS / Secret Manager

如果密钥曾经在聊天、日志或代码中暴露，请立即轮换。

## 本地配置

复制示例配置：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
AI_LLM_ENABLED=true
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-2025-08-07
OPENAI_BASE_URL=https://eu.aigw.galileo.roche.com/v1
OPENAI_API_KEY=<your-rotated-secret-key>
LLM_MATCHING_TEMPERATURE=0
LLM_MATCHING_TIMEOUT_SECONDS=60
```

启动服务：

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker 配置

确保 `.env` 存在，然后运行：

```bash
docker compose up --build
```

## LLM 在系统中的职责

LLM 可以：

- 理解 Speckit 需求文档
- 辅助匹配知识库场景
- 提取匹配证据
- 优化安全控制措施表达
- 辅助 Gate2 验证 Gate1 控制措施

LLM 不可以：

- 修改金标准知识库
- 新增或虚构知识库场景
- 降低阈值
- 强行匹配低置信度场景
- 自动 approve 报告

## Fallback 机制

如果 `AI_LLM_ENABLED=false` 或 LLM 调用失败，系统自动回退到确定性 MatchingEngine，不影响 Gate1/Gate2 基础评审能力。失败原因会写入 review JSON 的 `llm_error` 字段。
