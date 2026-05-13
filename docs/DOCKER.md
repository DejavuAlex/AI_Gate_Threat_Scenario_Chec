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

## Build with a pip mirror

Some enterprise or cloud hosts cannot reliably download packages from `pypi.org` / `files.pythonhosted.org`. Symptoms include:

```text
ReadTimeoutError
Connection reset by peer
ERROR: Could not find a version that satisfies the requirement pydantic==2.10.4
ERROR: No matching distribution found for pydantic==2.10.4
```

`pydantic==2.10.4` exists and supports Python 3.11. If you see the error above together with network timeout/reset messages, the root cause is usually package index connectivity rather than an invalid dependency.

The Dockerfile supports build-time pip mirror args:

```text
PIP_INDEX_URL
PIP_EXTRA_INDEX_URL
PIP_TRUSTED_HOST
```

### Official PyPI with longer timeout/retries

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://pypi.org/simple \
  -t localhost/ai-security-gate:latest .
```

### Tsinghua mirror example

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  -t localhost/ai-security-gate:latest .
```

### Enterprise PyPI mirror example

Prefer your approved internal Artifactory / Nexus / PyPI mirror when available:

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://<your-company-pypi-mirror>/simple \
  --build-arg PIP_TRUSTED_HOST=<your-company-pypi-mirror-hostname> \
  -t localhost/ai-security-gate:latest .
```

If your internal mirror is an extra source rather than the primary source:

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://pypi.org/simple \
  --build-arg PIP_EXTRA_INDEX_URL=https://<your-company-pypi-mirror>/simple \
  --build-arg PIP_TRUSTED_HOST=<your-company-pypi-mirror-hostname> \
  -t localhost/ai-security-gate:latest .
```

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

Build first. If the default PyPI route is unstable, use one of the mirror commands above.

```bash
podman build --no-cache --network=host \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  -t localhost/ai-security-gate:latest .
```

Then run:

```bash
podman run -d \
  --name ai-security-gate \
  -p 18080:8000 \
  -v ./reports:/app/reports:Z \
  -v ./data:/app/data:Z \
  -v ./knowledge_base:/app/knowledge_base:Z \
  -v ./specs:/app/specs:Z \
  --env-file .env \
  localhost/ai-security-gate:latest
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
docker build --no-cache \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
  -t ai-security-gate .

docker run -d \
  --name ai-security-gate \
  -p 18080:8000 \
  -v ./reports:/app/reports \
  -v ./data:/app/data \
  -v ./knowledge_base:/app/knowledge_base \
  -v ./specs:/app/specs \
  --env-file .env \
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

With direct Podman/Docker run, pass them using `--env-file .env`.

## Health check

After startup:

```bash
curl http://localhost:18080/api/v1/health
```

Expected response:

```json
{"status":"ok"}
```
