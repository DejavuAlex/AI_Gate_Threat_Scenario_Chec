# Development Guide

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run server

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run tests

```bash
python -m pytest -q
```

## Run Gate1 from CLI

```bash
python cli/security_gate_cli.py gate1 run \
  --docs specs/product-requirements.md specs/user-stories.md specs/business-flow.md \
  --threshold 0.78
```

## Run Gate2 from CLI

```bash
python cli/security_gate_cli.py gate2 run \
  --docs specs/architecture.md specs/api-design.md specs/data-model.md specs/implementation-plan.md \
  --gate1-report reports/Security-Review-Gate1.md \
  --threshold 0.78
```

## Notes

Generated review metadata is stored in `data/reviews/` and generated reports are stored in `reports/`. These generated runtime files are ignored by Git.
