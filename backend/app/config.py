from pathlib import Path
import os

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge_base"
REPORTS_DIR = REPO_ROOT / "reports"
DATA_DIR = REPO_ROOT / "data"
SPECS_DIR = REPO_ROOT / "specs"
REVIEWS_DIR = DATA_DIR / "reviews"
WORK_ORDERS_DIR = DATA_DIR / "work_orders"
TASKS_DIR = DATA_DIR / "tasks"
KB_HISTORY_DIR = DATA_DIR / "knowledge_base_history"
TASK_SEQUENCE_FILE = DATA_DIR / "task_sequence.json"

for directory in (REPORTS_DIR, DATA_DIR, SPECS_DIR, REVIEWS_DIR, WORK_ORDERS_DIR, TASKS_DIR, KB_HISTORY_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DEFAULT_THRESHOLD = 0.78
UNMATCHED_MESSAGE = "未匹配上任何威胁场景，本次安全评估确认无安全风险。"
DEFAULT_GATE2_DOCUMENTS = [
    "specs/architecture.md",
    "specs/api-design.md",
    "specs/data-model.md",
    "specs/implementation-plan.md",
]

# LLM configuration. Secrets must be provided by environment variables or .env,
# never committed to the repository.
AI_LLM_ENABLED = os.getenv("AI_LLM_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-2025-08-07")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://eu.aigw.galileo.roche.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MATCHING_TEMPERATURE = float(os.getenv("LLM_MATCHING_TEMPERATURE", "0"))
LLM_MATCHING_TIMEOUT_SECONDS = float(os.getenv("LLM_MATCHING_TIMEOUT_SECONDS", "60"))
