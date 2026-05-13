from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge_base"
REPORTS_DIR = REPO_ROOT / "reports"
DATA_DIR = REPO_ROOT / "data"
SPECS_DIR = REPO_ROOT / "specs"
REVIEWS_DIR = DATA_DIR / "reviews"

for directory in (REPORTS_DIR, DATA_DIR, SPECS_DIR, REVIEWS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

DEFAULT_THRESHOLD = 0.78
UNMATCHED_MESSAGE = "未匹配上任何威胁场景，本次安全评估确认无安全风险。"
