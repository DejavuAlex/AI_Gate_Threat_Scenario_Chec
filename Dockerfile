FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./

# Build-time pip mirror support. Use these args when the default PyPI route is
# slow, blocked, or proxied by an enterprise network:
#   podman build --network=host \
#     --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
#     --build-arg PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
#     -t localhost/ai-security-gate:latest .
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=
ARG PIP_TRUSTED_HOST=

RUN python -m pip install --upgrade pip && \
    if [ -n "$PIP_EXTRA_INDEX_URL" ] && [ -n "$PIP_TRUSTED_HOST" ]; then \
      pip install --retries 10 --timeout 120 \
        -i "$PIP_INDEX_URL" \
        --extra-index-url "$PIP_EXTRA_INDEX_URL" \
        --trusted-host "$PIP_TRUSTED_HOST" \
        -r requirements.txt; \
    elif [ -n "$PIP_EXTRA_INDEX_URL" ]; then \
      pip install --retries 10 --timeout 120 \
        -i "$PIP_INDEX_URL" \
        --extra-index-url "$PIP_EXTRA_INDEX_URL" \
        -r requirements.txt; \
    elif [ -n "$PIP_TRUSTED_HOST" ]; then \
      pip install --retries 10 --timeout 120 \
        -i "$PIP_INDEX_URL" \
        --trusted-host "$PIP_TRUSTED_HOST" \
        -r requirements.txt; \
    else \
      pip install --retries 10 --timeout 120 \
        -i "$PIP_INDEX_URL" \
        -r requirements.txt; \
    fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
