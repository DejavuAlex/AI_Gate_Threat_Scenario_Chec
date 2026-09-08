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

# Shared key for external API task submission and CI/CD pipeline calls.
# Local CLI agents never use this key. UI task submission uses dedicated UI routes.
AI_SECURITY_GATE_API_KEY = os.getenv("AI_SECURITY_GATE_API_KEY", "")

# LLM configuration. Secrets must be provided by environment variables or .env,
# never committed to the repository.
AI_LLM_ENABLED = os.getenv("AI_LLM_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-2025-08-07")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://eu.aigw.galileo.roche.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MATCHING_TEMPERATURE = float(os.getenv("LLM_MATCHING_TEMPERATURE", "0"))
LLM_MATCHING_TIMEOUT_SECONDS = float(os.getenv("LLM_MATCHING_TIMEOUT_SECONDS", "60"))

# Jira integration. The API token is a secret and must only come from the
# environment or .env; it is never returned by the API or written to a report.
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Task")
JIRA_TIMEOUT_SECONDS = float(os.getenv("JIRA_TIMEOUT_SECONDS", "30"))
# Optional: some Jira projects apply a hidden default Issue Security Level to
# new issues (via the project's security scheme) that the reporting account
# cannot see, making created issues invisible on dashboards. Set this to an
# security level id the reporting account can view/set to override that default.
JIRA_SECURITY_LEVEL_ID = os.getenv("JIRA_SECURITY_LEVEL_ID", "")
JIRA_VERIFY_SSL = os.getenv("JIRA_VERIFY_SSL", "true").lower() in {"1", "true", "yes", "on"}
JIRA_REQUEST_TIMEOUT = float(os.getenv("JIRA_REQUEST_TIMEOUT", str(JIRA_TIMEOUT_SECONDS)))
JIRA_ATTACHMENT_TIMEOUT = float(os.getenv("JIRA_ATTACHMENT_TIMEOUT", "60"))
JIRA_ATTACHMENT_MAX_BYTES = int(os.getenv("JIRA_ATTACHMENT_MAX_BYTES", str(20 * 1024 * 1024)))
# Jira squeezes wide tables into unreadable columns, so tables with more columns
# than this are transposed into one vertical field/value table per row. Set to 0
# to always keep the original horizontal layout.
JIRA_TABLE_TRANSPOSE_MIN_COLUMNS = int(os.getenv("JIRA_TABLE_TRANSPOSE_MIN_COLUMNS", "5"))
