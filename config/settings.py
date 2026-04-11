"""
Central configuration for AI Job Agent.
Reads secrets from GCP Secret Manager when running on GCP,
falls back to environment variables for local development.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
_GCP_AVAILABLE = False
try:
    from google.api_core.exceptions import GoogleAPICallError, NotFound, PermissionDenied  # type: ignore[assignment]
    _GCP_AVAILABLE = True
except ImportError:
    # GCP packages not installed (local dev / CI without GCP).
    # Use unique sentinel classes so exception handlers never accidentally
    # catch unrelated errors like TypeError or AttributeError.
    class NotFound(Exception):  # type: ignore[no-redef]
        pass

    class PermissionDenied(Exception):  # type: ignore[no-redef]
        pass

    class GoogleAPICallError(Exception):  # type: ignore[no-redef]
        pass

load_dotenv()

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "job_agent.db"
TEMPLATES_DIR = BASE_DIR / "src" / "templates"


# ── GCP Secret Manager ────────────────────────────────────────────────────
# When GCP_PROJECT_ID is set, secrets are fetched from Secret Manager.
# Falls back to os.getenv() when unset (local dev / Render).

GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")

_secret_client = None


def _get_secret_manager_client():
    """Lazy-init the Secret Manager client."""
    global _secret_client
    if _secret_client is None:
        from google.cloud import secretmanager
        _secret_client = secretmanager.SecretManagerServiceClient()
    return _secret_client


def get_secret(name: str, default: str = "", *, required: bool = False) -> str:
    """Fetch a secret from GCP Secret Manager, falling back to env vars.

    Lookup order:
      1. Environment variable (always wins, for local overrides)
      2. GCP Secret Manager (when GCP_PROJECT_ID is set)
      3. default value

    When required=True, GCP API errors (PermissionDenied, GoogleAPICallError)
    are re-raised. Otherwise, they are logged and the default is returned,
    preventing startup crashes for non-critical secrets.
    """
    env_val = os.getenv(name)
    if env_val is not None:
        return env_val

    if GCP_PROJECT_ID and _GCP_AVAILABLE:
        try:
            client = _get_secret_manager_client()
            secret_path = f"projects/{GCP_PROJECT_ID}/secrets/{name}/versions/latest"
            response = client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except NotFound:
            logger.debug(
                "Secret %s not found in Secret Manager, using default",
                name,
            )
        except PermissionDenied:
            logger.warning(
                "Permission denied reading secret %s from Secret Manager",
                name,
            )
            if required:
                raise
        except GoogleAPICallError:
            logger.warning(
                "Google API error reading secret %s from Secret Manager",
                name,
            )
            if required:
                raise

    return default


def _get_int_secret(name: str, default: int) -> int:
    """Fetch a secret and convert to int, with validation."""
    val = get_secret(name, str(default))
    try:
        return int(val)
    except ValueError:
        logger.warning("Invalid integer for %s: %r, using default %d", name, val, default)
        return default


# ── LLM provider ───────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = get_secret("ANTHROPIC_API_KEY")
OPENROUTER_API_KEY: str = get_secret("OPENROUTER_API_KEY")
AGENT_MODEL: str = get_secret("AGENT_MODEL", "claude-sonnet-4-6")
MAX_TOKENS: int = _get_int_secret("MAX_TOKENS", 4096)
USE_VERTEX_PRIMARY: bool = get_secret("USE_VERTEX_PRIMARY", "false").lower() == "true"

# Primary: OpenRouter. Fallback handled by llm_client.py.
USE_OPENROUTER: bool = bool(OPENROUTER_API_KEY)
LLM_API_KEY: str = OPENROUTER_API_KEY if USE_OPENROUTER else ANTHROPIC_API_KEY
LLM_BASE_URL = "https://openrouter.ai/api" if USE_OPENROUTER else None  # type: str | None

if not LLM_API_KEY and not USE_VERTEX_PRIMARY:
    import warnings
    warnings.warn(
        "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY, or enable USE_VERTEX_PRIMARY.",
        stacklevel=1,
    )

# ── Vertex AI (LLM failover) ──────────────────────────────────────────────
# Vertex AI uses Application Default Credentials (ADC) on GCP -- no API key.
# Locally, run `gcloud auth application-default login` or set
# GOOGLE_APPLICATION_CREDENTIALS to a service account key file.
VERTEX_PROJECT: str = get_secret("VERTEX_PROJECT", GCP_PROJECT_ID)
VERTEX_LOCATION: str = get_secret("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL: str = get_secret("VERTEX_MODEL", "claude-sonnet-4-6")
USE_VERTEX_FAILOVER: bool = get_secret("USE_VERTEX_FAILOVER", "false").lower() == "true"

if USE_VERTEX_PRIMARY and not VERTEX_PROJECT:
    import warnings
    warnings.warn(
        "USE_VERTEX_PRIMARY=true but VERTEX_PROJECT is empty. Set VERTEX_PROJECT for Vertex local testing.",
        stacklevel=1,
    )

# ── Database ───────────────────────────────────────────────────────────────
# Primary: Cloud SQL (PostgreSQL).  Failover: Supabase (PostgreSQL).
# When neither is set, falls back to local SQLite (dev mode).
DATABASE_URL: str = get_secret("DATABASE_URL")
DATABASE_URL_FAILOVER: str = get_secret("DATABASE_URL_FAILOVER")

# Supabase-specific keys (for future full switchover)
SUPABASE_URL: str = get_secret("SUPABASE_URL")
SUPABASE_KEY: str = get_secret("SUPABASE_KEY")
SUPABASE_SERVICE_KEY: str = get_secret("SUPABASE_SERVICE_KEY")

# ── Payments (Stripe) ─────────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = get_secret("STRIPE_SECRET_KEY")

# ── Auth (Cloud Identity Platform) ────────────────────────────────────────
AUTH_ENABLED: bool = get_secret("AUTH_ENABLED", "false").lower() == "true"
GCP_IDENTITY_PLATFORM_API_KEY: str = get_secret("GCP_IDENTITY_PLATFORM_API_KEY")

# ── Email (Resend) ────────────────────────────────────────────────────────
RESEND_API_KEY: str = get_secret("RESEND_API_KEY")
EMAIL_FROM: str = get_secret("EMAIL_FROM", "noreply@aviensolutions.com")

# ── Privacy ────────────────────────────────────────────────────────────────
ENCRYPT_USER_DATA: bool = get_secret("ENCRYPT_USER_DATA", "true").lower() == "true"

# ── Agent behaviour ────────────────────────────────────────────────────────
MAX_JOBS_PER_SEARCH: int = _get_int_secret("MAX_JOBS_PER_SEARCH", 25)
APPLICATION_COOLDOWN_DAYS: int = _get_int_secret("APPLICATION_COOLDOWN_DAYS", 30)

# ── Job search ────────────────────────────────────────────────────────────
JSEARCH_API_KEY: str = get_secret("JSEARCH_API_KEY")
ADZUNA_APP_ID: str = get_secret("ADZUNA_APP_ID")
ADZUNA_APP_KEY: str = get_secret("ADZUNA_APP_KEY")
_ADZUNA_VALID_COUNTRIES = {
    "at", "au", "be", "br", "ca", "ch", "de", "es", "fr", "gb",
    "in", "it", "mx", "nl", "nz", "pl", "ru", "sg", "us", "za",
}
_raw_adzuna_country = get_secret("ADZUNA_COUNTRY", "us").lower()
ADZUNA_COUNTRY: str = _raw_adzuna_country if _raw_adzuna_country in _ADZUNA_VALID_COUNTRIES else "us"
if _raw_adzuna_country not in _ADZUNA_VALID_COUNTRIES and _raw_adzuna_country:
    logger.warning("Invalid ADZUNA_COUNTRY=%r, defaulting to 'us'", _raw_adzuna_country)

# ── Bias-mitigation ───────────────────────────────────────────────────────
PROTECTED_ATTRIBUTES = {"gender", "age", "ethnicity", "religion", "nationality"}

# ── Environment ──────────────────────────────────────────────────────────
ENV: str = get_secret("ENV", "development").lower()


def validate_production_config() -> None:
    """Raise SystemExit if production is misconfigured."""
    if ENV == "production" and not AUTH_ENABLED:
        raise SystemExit(
            "FATAL: AUTH_ENABLED must be true when ENV=production. "
            "Refusing to start without authentication."
        )
    if ENV == "production" and ENCRYPT_USER_DATA:
        passphrase = os.getenv("PII_ENCRYPTION_PASSPHRASE", "")
        if not passphrase or passphrase == "jobagent-default-dev-key":
            raise SystemExit(
                "FATAL: PII_ENCRYPTION_PASSPHRASE must be set to a strong, unique value "
                "when ENV=production. The default key is publicly known."
            )
