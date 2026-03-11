"""
Central configuration for AI Job Agent.
Reads environment variables with safe defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "job_agent.db"
TEMPLATES_DIR = BASE_DIR / "src" / "templates"

# ── LLM provider ───────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4096"))

# When OPENROUTER_API_KEY is set, route all LLM calls through OpenRouter
USE_OPENROUTER: bool = bool(OPENROUTER_API_KEY)
LLM_API_KEY: str = OPENROUTER_API_KEY if USE_OPENROUTER else ANTHROPIC_API_KEY
LLM_BASE_URL: str | None = "https://openrouter.ai/api/v1" if USE_OPENROUTER else None

# ── Privacy ────────────────────────────────────────────────────────────────
# When True, PII is stored encrypted at rest; key derived from user passphrase
ENCRYPT_USER_DATA: bool = os.getenv("ENCRYPT_USER_DATA", "true").lower() == "true"

# ── Agent behaviour ────────────────────────────────────────────────────────
MAX_JOBS_PER_SEARCH: int = int(os.getenv("MAX_JOBS_PER_SEARCH", "25"))
APPLICATION_COOLDOWN_DAYS: int = int(os.getenv("APPLICATION_COOLDOWN_DAYS", "30"))

# ── Bias-mitigation ───────────────────────────────────────────────────────
# Fields that the recommender must never use as ranking signals
PROTECTED_ATTRIBUTES = {"gender", "age", "ethnicity", "religion", "nationality"}
