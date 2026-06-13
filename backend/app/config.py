import json
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"  # backend/.env
load_dotenv(dotenv_path=ENV_PATH, override=False)
def getenv_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TEXT_MODEL = os.getenv("TEXT_MODEL")
IMAGE_MODEL = os.getenv("IMAGE_MODEL")
IMAGE_SIZE = os.getenv("IMAGE_SIZE")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru")
ENABLE_IMAGE_GENERATION = getenv_bool("ENABLE_IMAGE_GENERATION", True)

JWT_SECRET = os.getenv("JWT_SECRET")
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "720"))
# For security, default to not auto-registering on login unless explicitly enabled
AUTO_REGISTER_ON_LOGIN = getenv_bool("AUTO_REGISTER_ON_LOGIN", False)
VERIFY_EMAIL_TTL_MINUTES = int(os.getenv("VERIFY_EMAIL_TTL_MINUTES", "60"))

def _normalize_database_url(url: str) -> str:
    """Use psycopg v3 (requirements: psycopg[binary]), not psycopg2."""
    u = (url or "").strip()
    if u.startswith("postgres://"):
        return "postgresql+psycopg://" + u[len("postgres://") :]
    if u.startswith("postgresql://"):
        return "postgresql+psycopg://" + u[len("postgresql://") :]
    if u.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + u[len("postgresql+psycopg2://") :]
    return u


def _is_render_deployment() -> bool:
    """Render sets RENDER=true on web services."""
    return getenv_bool("RENDER", False) or bool(os.getenv("RENDER_SERVICE_ID", "").strip())


def _resolve_database_url() -> str:
    """
    Local dev: SQLite by default (works offline, no Render Postgres needed).
    Render: DATABASE_URL from the service environment (linked Postgres).
    Set USE_POSTGRES_LOCALLY=true in .env to point local runs at DATABASE_URL anyway.
    """
    postgres_url = (os.getenv("DATABASE_URL") or "").strip()
    local_default = (os.getenv("LOCAL_DATABASE_URL") or "sqlite:///./app.db").strip()

    if _is_render_deployment():
        if not postgres_url:
            return _normalize_database_url(local_default)
        return _normalize_database_url(postgres_url)

    if getenv_bool("USE_POSTGRES_LOCALLY", False) and postgres_url:
        return _normalize_database_url(postgres_url)

    return _normalize_database_url(local_default)


DATABASE_URL = _resolve_database_url()
IS_LOCAL_SQLITE = DATABASE_URL.startswith("sqlite")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# Path to the static frontend directory (contains *.html and assets/)
FRONTEND_DIR = os.getenv("FRONTEND_DIR", "../frontend")

# Cloudflare R2 (S3-compatible object storage)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_REGION = os.getenv("R2_REGION", "auto")
R2_ENDPOINT = os.getenv(
    "R2_ENDPOINT",
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else None,
)
# Public base URL for serving objects (e.g. https://static.example.com or
# https://<bucket>.<accountid>.r2.cloudflarestorage.com). If not set, we fall
# back to a default based on bucket/account when possible.
R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL")

# SendGrid verification email settings
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
# When false: no verification emails, users are verified on register, login is not blocked.
# REQUIRE_EMAIL_VERIFICATION takes precedence; SENDGRID_ENFORCE_VERIFIED_LOGIN is a legacy alias.
if os.getenv("REQUIRE_EMAIL_VERIFICATION") is not None:
    REQUIRE_EMAIL_VERIFICATION = getenv_bool("REQUIRE_EMAIL_VERIFICATION", True)
else:
    REQUIRE_EMAIL_VERIFICATION = getenv_bool("SENDGRID_ENFORCE_VERIFIED_LOGIN", True)
SENDGRID_ENFORCE_VERIFIED_LOGIN = REQUIRE_EMAIL_VERIFICATION
# Public app URL used to build verification links (e.g. https://app.example.com)
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# PayPal (sandbox/prod via PAYPAL_ENV)
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_PLAN_ID = os.getenv("PAYPAL_PLAN_ID")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")
PAYPAL_ENV = os.getenv("PAYPAL_ENV", "sandbox").strip().lower()

# Token economy (server-enforced; never accept balance from clients)
TOKENS_PER_TEXT = max(1, int(os.getenv("TOKENS_PER_TEXT", "10")))
TOKENS_PER_IMAGE = max(1, int(os.getenv("TOKENS_PER_IMAGE", "20")))
# Global reference price per token (USD) for display; plan top-up rates may differ
TOKEN_USD_REFERENCE = max(0.0001, float(os.getenv("TOKEN_USD_REFERENCE", "0.012")))
FREE_PLAN_GENERATIONS_PER_DAY = max(0, int(os.getenv("FREE_PLAN_GENERATIONS_PER_DAY", "1")))

_DEFAULT_TOKEN_PLANS = [
    {
        "id": "free",
        "name": "Free",
        "isFree": True,
        "tokens": 0,
        "priceUsdCents": 0,
        "freeGenerationsPerDay": 1,
        "cycleLabel": "",
        "paypalPlanId": "",
        "description": "1 generation per day · fewer variants · no token top-ups",
    },
    {
        "id": "pro_monthly",
        "name": "Pro",
        "isFree": False,
        "tokens": 1000,
        "priceUsdCents": 1000,
        "extraTokenUsdPerToken": 0.012,
        "cycleLabel": "month",
        "paypalPlanId": "",
        "description": "1,000 tokens per month · buy extra tokens at plan rate",
    },
]


def _load_token_plans() -> list[dict]:
    raw = (os.getenv("TOKEN_PLANS_JSON") or "").strip()
    if not raw:
        plans = [dict(p) for p in _DEFAULT_TOKEN_PLANS]
    else:
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list) or not parsed:
                plans = [dict(p) for p in _DEFAULT_TOKEN_PLANS]
            else:
                plans = [dict(p) for p in parsed if isinstance(p, dict)]
        except Exception:
            plans = [dict(p) for p in _DEFAULT_TOKEN_PLANS]
    paypal_fallback = (PAYPAL_PLAN_ID or "").strip()
    for plan in plans:
        if not (plan.get("paypalPlanId") or "").strip() and paypal_fallback:
            plan["paypalPlanId"] = paypal_fallback
        plan["tokens"] = max(0, int(plan.get("tokens") or 0))
        plan["priceUsdCents"] = max(0, int(plan.get("priceUsdCents") or 0))
        extra = plan.get("extraTokenUsdPerToken")
        if extra is None or extra == "":
            plan["extraTokenUsdPerToken"] = TOKEN_USD_REFERENCE
        else:
            plan["extraTokenUsdPerToken"] = max(0.0001, float(extra))
        if not (plan.get("id") or "").strip():
            plan["id"] = "plan"
        plan["isFree"] = bool(plan.get("isFree"))
        if plan["isFree"]:
            plan["freeGenerationsPerDay"] = max(
                0,
                int(plan.get("freeGenerationsPerDay") or FREE_PLAN_GENERATIONS_PER_DAY),
            )
    return plans


def paid_token_plans() -> list[dict]:
    return [p for p in TOKEN_PLANS if not p.get("isFree")]


def free_token_plan() -> dict | None:
    for p in TOKEN_PLANS:
        if p.get("isFree"):
            return p
    return None


TOKEN_PLANS = _load_token_plans()

# Account reputation (content-policy violations lower score; payment restores)
REPUTATION_DEFAULT = max(0, min(100, int(os.getenv("REPUTATION_DEFAULT", "100"))))
REPUTATION_PENALTY_CONTENT_POLICY = max(
    1, int(os.getenv("REPUTATION_PENALTY_CONTENT_POLICY", "10"))
)
REPUTATION_ORANGE_THRESHOLD = max(
    1, min(99, int(os.getenv("REPUTATION_ORANGE_THRESHOLD", "40")))
)
REPUTATION_RECOVERY_AMOUNT = max(
    1, int(os.getenv("REPUTATION_RECOVERY_AMOUNT", "10"))
)
REPUTATION_RECOVERY_HOURS = max(1, int(os.getenv("REPUTATION_RECOVERY_HOURS", "24")))
REPUTATION_BILLING_PERIOD_DAYS = max(1, int(os.getenv("REPUTATION_BILLING_PERIOD_DAYS", "30")))
# Support/admin API key for refund review (header: X-Admin-Key)
ADMIN_API_KEY = (os.getenv("ADMIN_API_KEY") or "").strip()

# Compliance / data-retention controls
REQUIRE_LEGAL_CONSENT_AT_REGISTER = getenv_bool("REQUIRE_LEGAL_CONSENT_AT_REGISTER", True)
RETENTION_JOBS_DAYS = int(os.getenv("RETENTION_JOBS_DAYS", "30"))
RETENTION_SESSIONS_DAYS = int(os.getenv("RETENTION_SESSIONS_DAYS", "30"))
RETENTION_LOGS_DAYS = int(os.getenv("RETENTION_LOGS_DAYS", "30"))
RETENTION_GENERATED_EMAILS_DAYS = int(os.getenv("RETENTION_GENERATED_EMAILS_DAYS", "365"))
