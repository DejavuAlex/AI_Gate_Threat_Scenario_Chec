# Docker / Podman Deployment Guide

## Why `docker compose up --build` may fail on some Linux hosts

If your server prints output similar to:

```text
Emulate Docker CLI using podman. Create /etc/containers/nodocker to quiet msg.
Error: looking up compose provider failed
exec: "docker-compose": executable file not found in $PATH
exec: "podman-compose": executable file not found in $PATH
```

then the `docker` command on that host is a Podman compatibility wrapper, not Docker Engine with Docker Compose installed. The wrapper can run many `docker` commands, but it still needs either `docker-compose`, Docker Compose v2 plugin, or `podman-compose` to run Compose files.

## Recommended host port

The container listens internally on port `8000`, but `docker-compose.yml` publishes it to host port `18080` by default:

```text
http://localhost:18080
```

You can override the host port with `.env`:

```bash
cp .env.example .env
# edit .env
AI_SECURITY_GATE_HOST_PORT=18081
```

Then run compose again.

## Option A: Install podman-compose

For RHEL/CentOS/Alibaba Cloud Linux style hosts, try one of the following:

```bash
yum install -y podman-compose
```

or:

```bash
dnf install -y podman-compose
```

If the package is not available:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install podman-compose
```

Run:

```bash
podman-compose up --build
```

Open:

```text
http://<server-ip>:18080
```

## Option B: Install Docker Engine + Compose plugin

If you prefer Docker Engine, install Docker and the Compose plugin for your OS, then verify:

```bash
docker --version
docker compose version
```

Run:

```bash
docker compose up --build
```

Open:

```text
http://<server-ip>:18080
```

## Option C: Run with Podman without Compose

You can bypass Compose completely:

```bash
podman build -t ai-security-gate .

podman run -d \
  --name ai-security-gate \
  -p 18080:8000 \
  -v ./reports:/app/reports:Z \
  -v ./data:/app/data:Z \
  -v ./knowledge_base:/app/knowledge_base:Z \
  -v ./specs:/app/specs:Z \
  -e AI_LLM_ENABLED=false \
  ai-security-gate
```

If SELinux is disabled or the `:Z` suffix causes issues, remove `:Z` from the volume mounts.

Check logs:

```bash
podman logs -f ai-security-gate
```

Stop and remove:

```bash
podman stop ai-security-gate
podman rm ai-security-gate
```

## Option D: Run with Docker without Compose

```bash
docker build -t ai-security-gate .

docker run -d \
  --name ai-security-gate \
  -p 18080:8000 \
  -v ./reports:/app/reports \
  -v ./data:/app/data \
  -v ./knowledge_base:/app/knowledge_base \
  -v ./specs:/app/specs \
  -e AI_LLM_ENABLED=false \
  ai-security-gate
```

Check logs:

```bash
docker logs -f ai-security-gate
```

## Enable LLM in container mode

Create `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
AI_SECURITY_GATE_HOST_PORT=18080
AI_LLM_ENABLED=true
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-2025-08-07
OPENAI_BASE_URL=https://eu.aigw.galileo.roche.com/v1
OPENAI_API_KEY=<your-secret-key>
LLM_MATCHING_TEMPERATURE=0
LLM_MATCHING_TIMEOUT_SECONDS=60
```

With Compose, variables are read automatically from `.env`.

With direct Podman/Docker run, pass them using `--env-file .env`:

```bash
podman run -d --name ai-security-gate -p 18080:8000 --env-file .env ai-security-gate
```

## Health check

After startup:

```bash
curl http://localhost:18080/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```
