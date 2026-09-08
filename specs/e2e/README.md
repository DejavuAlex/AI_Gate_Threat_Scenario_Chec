# AI-Gate Synthetic E2E Scenarios

These specifications are synthetic, non-production fixtures for deterministic AI-Gate validation.

| Scenario folder | Product type | Knowledge base ID | Positive Gate1/Gate2 coverage |
|---|---|---|---|
| `cloud-saas` | Public cloud SaaS | `cloud-service-sample` | Object storage upload and cloud API identity |
| `on-premise` | Localized / air-gapped product | `on-premise-product` | Local administration, offline update, enterprise directory |
| `mobile-health` | Mobile healthcare application | `mobile-health-product` | Deep links, offline clinical cache, biometric sign-in |
| `ai-knowledge-assistant` | RAG and tool-using AI product | `ai-knowledge-assistant` | Prompt injection, retrieval isolation, agent tools |
| `negative-control` | Stateless offline utility | all fixture KBs | Expected to match no scenario |

Each positive folder contains three Gate1 business documents and four Gate2 design documents. The implementation plan repeats the Gate1 control wording so Gate2 traceability can be checked deterministically.

Run the automated suite with `pytest -q tests/test_synthetic_scenario_e2e.py`. Run the same workflow against a deployed instance with `python scripts/run_synthetic_e2e.py --base-url http://localhost:18082`.
