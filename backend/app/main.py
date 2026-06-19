

import asyncio
import base64
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Depends, HTTPException, UploadFile, File, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, text, func
import httpx

from app.config import (
    FRONTEND_DIR,
    OPENAI_API_KEY,
    AUTO_REGISTER_ON_LOGIN,
    DEFAULT_LANGUAGE,
    EMAIL_PROVIDER,
    LLM_PROVIDER,
    UNISENDER_API_KEY,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    SENDGRID_UNSUBSCRIBE_URL,
    REQUIRE_EMAIL_VERIFICATION,
    APP_BASE_URL,
    VERIFY_EMAIL_TTL_MINUTES,
    PAYPAL_CLIENT_ID,
    PAYPAL_CLIENT_SECRET,
    PAYPAL_PLAN_ID,
    PAYPAL_WEBHOOK_ID,
    PAYPAL_ENV,
    REQUIRE_LEGAL_CONSENT_AT_REGISTER,
    RETENTION_JOBS_DAYS,
    RETENTION_SESSIONS_DAYS,
    RETENTION_LOGS_DAYS,
    RETENTION_GENERATED_EMAILS_DAYS,
    ADMIN_API_KEY,
    IS_LOCAL_SQLITE,
    _is_render_deployment,
)
from app.billing import (
    PROTECTED_PROFILE_SETTINGS_KEYS,
    FAILURE_CONTENT_POLICY,
    FAILURE_SERVER,
    activate_subscription_plan,
    billing_json,
    can_request_refund,
    charge_for_generation,
    charge_for_refine,
    create_refund_request,
    entitlements_for_user,
    fulfill_paypal_payment,
    fulfill_token_topup,
    generation_token_cost,
    handle_generation_failure,
    job_refund_status,
    mark_billing_refunded,
    parse_billing_json,
    parse_topup_custom_id,
    plan_by_id,
    plan_is_free,
    public_free_plan,
    public_plans,
    resolve_refund_request,
    topup_price_usd,
    get_token_balance,
)
from app.db import Base, engine, get_db, SessionLocal
from app.models import (
    User,
    CompanyProfile,
    GenerationSession,
    GenerationLog,
    GenerationJob,
    GeneratedEmail,
    UserProfile,
    UserSession,
    EmailVerificationToken,
    TokenRefundRequest,
    UserTemplate,
)
from app.schemas import (
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    LoginRequest,
    LoginResponse,
    CompanyProfileSchema,
    TemplateItem,
    GenerateRequest,
    GenerateJobStarted,
    GenerateJobListItem,
    RefineRequest,
    GenerationResult,
    ExportRequest,
    AccountSettingsResponse,
    AccountSettingsUpdateRequest,
    Entitlements,
    PasswordUpdateRequest,
    UserSessionItem,
    GeneratedEmailListItem,
    GeneratedEmailDetail,
    GeneratedEmailUpdateRequest,
    GeneratedEmailCreateRequest,
    TokenRefundRequestCreate,
    TokenRefundRequestItem,
    AdminRefundResolveRequest,
    TokenTopUpRequest,
    GenerationCostQuoteResponse,
    RenderPreviewRequest,
    UserTemplateItem,
    UserTemplateCreateRequest,
    UserTemplateUpdateRequest,
    ContactsUploadRequest,
    ContactsUploadResultItem,
    ContactListCreate,
    ContactsSendCampaignRequest,
    ContactsSendCampaignResult,
    CampaignStatItem,
    CampaignStatsResponse,
)
from app.auth import hash_password, verify_password, create_access_token, decode_token
from app.generator import generate_pack, generate_block_content, to_generation_result, llm_is_configured
from app import email_dispatch
from app.storage import upload_image_bytes_to_r2
from app.template_renderer import render_template
from app.modular_presets import MODULAR_TEMPLATE_DEFS, object_counts_from_layout
from app.modular_renderer import render_modular_email
from app.email_builder.registry import BLOCK_REGISTRY
from app.template_security import (
    MAX_USER_TEMPLATES_PER_USER,
    TemplateValidationError,
    sanitize_preview_body_html,
    sanitize_preview_subject,
    sanitize_string,
    sanitize_template_name,
    sanitize_theme,
    sanitize_url,
    validate_block_layout,
)
from app.blocks_i18n import localized_blocks

app = FastAPI(title="smart-letters Backend")

# CORS (safe for local dev; tighten for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _no_store_api_responses(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api") or path.endswith(".js"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


Base.metadata.create_all(bind=engine)


def _sqlite_migrate_schema() -> None:
    """
    Lightweight migrations for SQLite dev DBs.
    SQLAlchemy create_all() does not ALTER existing tables when new columns are added.
    """
    url = str(engine.url)
    if not url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(generation_sessions)")).fetchall()
        if not rows:
            return
        col_names = {r[1] for r in rows}
        if "generated_email_id" not in col_names:
            conn.execute(
                text("ALTER TABLE generation_sessions ADD COLUMN generated_email_id INTEGER")
            )
        user_rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        user_col_names = {r[1] for r in user_rows}
        if "email_verified" not in user_col_names:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0")
            )
            # Existing users were created before verification was introduced.
            conn.execute(text("UPDATE users SET email_verified = 1"))
        profile_rows = conn.execute(text("PRAGMA table_info(user_profiles)")).fetchall()
        if profile_rows:
            profile_cols = {r[1] for r in profile_rows}
            if "token_balance" not in profile_cols:
                conn.execute(
                    text(
                        "ALTER TABLE user_profiles ADD COLUMN token_balance INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "reputation_score" not in profile_cols:
                conn.execute(
                    text(
                        "ALTER TABLE user_profiles ADD COLUMN reputation_score INTEGER NOT NULL DEFAULT 100"
                    )
                )
            if "reputation_last_recovery_at" not in profile_cols:
                conn.execute(
                    text(
                        "ALTER TABLE user_profiles ADD COLUMN reputation_last_recovery_at DATETIME"
                    )
                )
        job_rows = conn.execute(text("PRAGMA table_info(generation_jobs)")).fetchall()
        if job_rows:
            job_cols = {r[1] for r in job_rows}
            if "billing_json" not in job_cols:
                conn.execute(
                    text(
                        "ALTER TABLE generation_jobs ADD COLUMN billing_json TEXT NOT NULL DEFAULT '{}'"
                    )
                )
            if "failure_kind" not in job_cols:
                conn.execute(
                    text(
                        "ALTER TABLE generation_jobs ADD COLUMN failure_kind VARCHAR(32) NOT NULL DEFAULT ''"
                    )
                )
        # Custom-template tables/migrations removed.


_sqlite_migrate_schema()

_RESEND_RATE_LIMIT: dict[str, datetime] = {}
BUILTIN_TEMPLATE_DEFS = {
    **MODULAR_TEMPLATE_DEFS,
}


def _user_template_public_id(row_id: int) -> str:
    return f"user:{row_id}"


def _parse_user_template_id(template_id: str | None) -> int | None:
    tid = (template_id or "").strip()
    if not tid.startswith("user:"):
        return None
    try:
        return int(tid.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


def _load_user_template_row(db: Session, user_id: int, template_id: str | None) -> UserTemplate | None:
    row_id = _parse_user_template_id(template_id)
    if row_id is None:
        return None
    row = db.get(UserTemplate, row_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def _user_template_to_item(row: UserTemplate) -> dict:
    try:
        layout = json.loads(row.layout_json or "[]")
    except Exception:
        layout = []
    try:
        theme = json.loads(row.theme_json or "{}")
    except Exception:
        theme = {}
    if not isinstance(layout, list):
        layout = []
    if not isinstance(theme, dict):
        theme = {}
    updated = row.updated_at.isoformat() if hasattr(row.updated_at, "isoformat") else str(row.updated_at or "")
    primary = str(theme.get("primary") or "4f46e5").lstrip("#")
    return {
        "id": _user_template_public_id(row.id),
        "name": row.name,
        "previewImageUrl": f"https://placehold.co/600x400/{primary}/ffffff?text=My+template",
        "objectCounts": object_counts_from_layout(layout),
        "theme": theme,
        "isModular": bool(row.is_modular),
        "blockLayout": layout,
        "isBuiltin": False,
        "userTemplateId": row.id,
    }


def _apply_user_template_to_request(db: Session, user_id: int, req: GenerateRequest) -> None:
    row = _load_user_template_row(db, user_id, req.templateId)
    if row is None:
        return
    try:
        layout = json.loads(row.layout_json or "[]")
    except Exception:
        layout = []
    try:
        theme = json.loads(row.theme_json or "{}")
    except Exception:
        theme = {}
    if isinstance(layout, list) and layout and not req.blockLayout:
        req.blockLayout = layout
    if isinstance(theme, dict) and theme.get("colorScheme"):
        req.colorScheme = theme.get("colorScheme")


def _template_def(template_id: str | None, db: Session | None = None, user_id: int | None = None) -> dict:
    if db is not None and user_id is not None:
        row = _load_user_template_row(db, user_id, template_id)
        if row is not None:
            return _user_template_to_item(row)
    _fallback = next(iter(BUILTIN_TEMPLATE_DEFS.values()), {})
    return BUILTIN_TEMPLATE_DEFS.get((template_id or "").strip(), _fallback)


def _is_modular_template(template_id: str | None) -> bool:
    return bool(_template_def(template_id).get("isModular"))


def _resolve_block_layout(template_id: str | None, block_layout_override: list | None = None) -> list[dict]:
    if block_layout_override:
        return validate_block_layout(block_layout_override)
    d = _template_def(template_id)
    layout = d.get("blockLayout") or []
    return validate_block_layout([dict(b) for b in layout if isinstance(b, dict)])


def _validate_generate_block_layout(req: GenerateRequest) -> None:
    if not req.blockLayout:
        return
    try:
        req.blockLayout = validate_block_layout(req.blockLayout)
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _object_counts_for_template(
    template_id: str | None,
    block_layout: list | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict:
    if block_layout:
        return object_counts_from_layout(block_layout)
    d = _template_def(template_id, db, user_id)
    if d.get("isModular") and d.get("blockLayout"):
        return object_counts_from_layout(d.get("blockLayout"))
    return dict(d.get("objectCounts") or {})


def _template_config_for_render(template_id: str | None, block_layout: list | None = None) -> dict:
    d = _template_def(template_id)
    if d.get("isModular"):
        layout = _resolve_block_layout(template_id, block_layout)
        return {"theme": dict(d.get("theme", {})), "blocks": [], "blockLayout": layout, "isModular": True}
    counts = d.get("objectCounts", {})
    blocks = [
        {"id": "heading", "type": "heading", "enabled": bool(counts.get("header", 0) > 0), "props": {"align": "left"}},
        {"id": "logo", "type": "logo", "enabled": True, "props": {"size": "md"}},
        {"id": "image", "type": "image", "enabled": bool(counts.get("image", 0) > 0), "props": {"rounded": True}},
        {"id": "body", "type": "body", "enabled": bool(counts.get("body", 0) > 0), "props": {"fontSize": 16}},
        {"id": "cta", "type": "cta", "enabled": bool(counts.get("cta", 0) > 0), "props": {"style": "solid"}},
        {"id": "footer", "type": "footer", "enabled": bool(counts.get("footer", 0) > 0), "props": {"showSocials": True}},
    ]
    return {"theme": dict(d.get("theme", {})), "blocks": blocks}


def _cleanup_old_data(db: Session) -> None:
    now = datetime.now(timezone.utc)
    try:
        if RETENTION_JOBS_DAYS > 0:
            cutoff = now - timedelta(days=RETENTION_JOBS_DAYS)
            db.query(GenerationJob).filter(GenerationJob.created_at < cutoff).delete()
        if RETENTION_SESSIONS_DAYS > 0:
            cutoff = now - timedelta(days=RETENTION_SESSIONS_DAYS)
            db.query(GenerationSession).filter(GenerationSession.created_at < cutoff).delete()
        if RETENTION_LOGS_DAYS > 0:
            cutoff = now - timedelta(days=RETENTION_LOGS_DAYS)
            db.query(GenerationLog).filter(GenerationLog.created_at < cutoff).delete()
        if RETENTION_GENERATED_EMAILS_DAYS > 0:
            cutoff = now - timedelta(days=RETENTION_GENERATED_EMAILS_DAYS)
            db.query(GeneratedEmail).filter(GeneratedEmail.created_at < cutoff).delete()
        db.commit()
    except Exception:
        db.rollback()


@app.on_event("startup")
def _startup_retention_cleanup() -> None:
    missing = []
    if not llm_is_configured():
        missing.append("GIGACHAT_AUTH_KEY" if LLM_PROVIDER == "gigachat" else "OPENAI_API_KEY")
    if EMAIL_PROVIDER == "unisender":
        if not UNISENDER_API_KEY:
            missing.append("UNISENDER_API_KEY")
    else:
        if not SENDGRID_API_KEY:
            missing.append("SENDGRID_API_KEY")
        if not SENDGRID_FROM_EMAIL:
            missing.append("SENDGRID_FROM_EMAIL")
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET or not PAYPAL_PLAN_ID:
        missing.append("PAYPAL_*")
    if missing:
        print(f"[startup] warning: missing config keys: {', '.join(missing)}")
    if _is_render_deployment():
        print("[startup] database: postgres (Render)")
    elif IS_LOCAL_SQLITE:
        print("[startup] database: sqlite (local dev)")
    else:
        print("[startup] database: postgres (local override)")
    db = SessionLocal()
    try:
        _cleanup_old_data(db)
    finally:
        db.close()


def _profile_settings_dict(db: Session, user_id: int) -> dict:
    profile = db.get(UserProfile, user_id)
    if not profile or not profile.settings_json:
        return {}
    try:
        return json.loads(profile.settings_json)
    except Exception:
        return {}


def _write_profile_settings(db: Session, user_id: int, settings: dict) -> None:
    profile = db.get(UserProfile, user_id)
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    profile.settings_json = json.dumps(settings or {}, ensure_ascii=False)
    db.commit()


def _entitlements_for_user(db: Session, user: User) -> Entitlements:
    settings = _profile_settings_dict(db, user.id)
    return entitlements_for_user(db, user.id, settings=settings)


def _image_policy_user_message(lang: str) -> str:
    lang = (lang or "").lower()
    if lang in ("en", "eng", "english"):
        return (
            "Your image prompt violates OpenAI content policy. "
            "Please rephrase your image wishes."
        )
    return (
        "Ваш запрос к изображению нарушает политику OpenAI. "
        "Пожалуйста, переформулируйте пожелания к картинке."
    )


def _apply_job_failure(
    db: Session,
    job: GenerationJob,
    user_id: int,
    billing: dict,
    failure_kind: str,
    base_message: str,
    lang: str,
) -> None:
    extra = handle_generation_failure(
        db,
        user_id=user_id,
        billing=billing,
        failure_kind=failure_kind,
        lang=lang,
    )
    job.status = "error"
    job.step_key = "error"
    job.failure_kind = failure_kind
    if failure_kind == FAILURE_CONTENT_POLICY:
        job.error_message = (extra or base_message or "Content policy violation")[:4000]
    else:
        job.error_message = (base_message or "Generation failed")[:4000]
        if int(billing.get("tokensCharged") or 0) > 0:
            job.billing_json = json.dumps(mark_billing_refunded(billing), ensure_ascii=False)


def _require_admin(request: Request) -> None:
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="Admin API is not configured")
    if (request.headers.get("X-Admin-Key") or "").strip() != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


def _company_profile_for_user(db: Session, user_id: int) -> dict:
    prof = db.get(CompanyProfile, user_id)
    if not prof or not prof.data_json:
        return {}
    try:
        return json.loads(prof.data_json)
    except Exception:
        return {}


def _generation_caps_from_billing(billing: dict) -> tuple[int, int]:
    paid = (billing.get("mode") or "") == "tokens"
    return (3 if paid else 2), (3 if paid else 1)


def _template_generation_requirements(
    template_id: str | None,
    block_layout: list | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict:
    counts = _object_counts_for_template(template_id, block_layout, db, user_id)
    return {
        "body_count": max(0, int(counts.get("body", 1) or 0)),
        "cta_count": max(0, int(counts.get("cta", 1) or 0)),
        "image_count": max(0, int(counts.get("image", 1) or 0)),
    }


def _result_with_layout(
    result: GenerationResult,
    template_id: str,
    block_layout: list | None = None,
) -> GenerationResult:
    if not _is_modular_template(template_id):
        return result
    layout = _resolve_block_layout(template_id, block_layout)
    if not layout:
        return result
    data = result.model_dump()
    data["isModular"] = True
    data["blockLayout"] = layout
    return GenerationResult.model_validate(data)


def _attach_block_content(
    result: GenerationResult,
    *,
    template_id: str,
    block_layout: list | None,
    company_profile: dict,
    subject: str,
    body_html: str,
    language: str,
) -> GenerationResult:
    """Generate per-element text content for composite blocks and attach it to the result.

    Degrades gracefully: any failure leaves blockContent empty (renderer falls back to
    distributing generated images and clearing placeholders).
    """
    if not _is_modular_template(template_id):
        return result
    try:
        layout = _resolve_block_layout(template_id, block_layout)
        block_content = generate_block_content(
            layout=layout,
            company_profile=company_profile,
            subject=subject,
            body_html=body_html,
            language=language,
        )
    except Exception as exc:  # noqa: BLE001 - never fail generation over block content
        print("attach block content error:", repr(exc))
        return result
    if not block_content:
        return result
    data = result.model_dump()
    # JSON object keys must be strings.
    data["blockContent"] = {str(k): v for k, v in block_content.items()}
    return GenerationResult.model_validate(data)


def _call_pack_and_result(
    *,
    company_profile: dict,
    req: GenerateRequest,
    session_id: str,
    variant_count_cap: int,
    image_slots_cap: int,
    requirements: dict,
    images_allowed: bool = True,
) -> GenerationResult:
    body_count = max(0, int(requirements.get("body_count", 0)))
    cta_count = max(0, int(requirements.get("cta_count", 0)))
    image_count = max(0, int(requirements.get("image_count", 0)))
    needed_variants = max(body_count, cta_count, image_count, 1)
    variant_count = max(1, min(int(variant_count_cap or 1), needed_variants))
    image_slots = 0 if not images_allowed else max(0, min(int(image_slots_cap or 0), image_count))
    pack = generate_pack(
        company_profile=company_profile,
        subject=req.subject,
        image_wishes=req.imageWishes,
        cta_link=req.ctaLink,
        color_scheme=req.colorScheme,
        template_id=req.templateId,
        language=(req.language or DEFAULT_LANGUAGE),
        feedback=None,
        variant_count=variant_count,
        need_body=body_count > 0,
        need_cta=cta_count > 0,
        need_image=image_slots > 0,
    )
    return to_generation_result(
        session_id=session_id,
        template_id=req.templateId,
        pack=pack,
        cta_link=req.ctaLink,
        subject=req.subject,
        color_scheme=req.colorScheme,
        language=req.language or DEFAULT_LANGUAGE,
        image_option_count=image_slots,
        text_option_count=body_count,
        cta_option_count=cta_count,
    )


def _persist_generation_bundle(
    db: Session,
    user: User,
    req: GenerateRequest,
    session_id: str,
    result: GenerationResult,
) -> None:
    generated = GeneratedEmail(
        user_id=user.id,
        title=req.subject[:120] if req.subject else "Generated email",
        subject=req.subject or "",
        template_id=req.templateId,
        payload_json=result.model_dump_json(),
        html_snapshot="",
    )
    db.add(generated)
    db.flush()
    db.add(
        GenerationSession(
            session_id=session_id,
            user_id=user.id,
            generation_json=result.model_dump_json(),
            generated_email_id=generated.id,
        )
    )
    db.commit()


def _job_progress_step(step_key: str) -> int:
    return {"queued": 0, "text": 1, "image": 2, "saving": 3, "done": 3, "error": 0}.get(step_key or "queued", 0)


def _job_started_at_iso(job: GenerationJob) -> str | None:
    ca = job.created_at
    if ca is None:
        return None
    if hasattr(ca, "isoformat"):
        try:
            return ca.isoformat()
        except Exception:
            return str(ca)
    return str(ca)


def _job_estimate_remaining_seconds(job: GenerationJob) -> int | None:
    if job.status in ("done", "error"):
        return None if job.status == "error" else 0
    ca = job.created_at
    if ca is None:
        return 60
    try:
        if isinstance(ca, datetime) and ca.tzinfo is not None:
            elapsed = (datetime.now(timezone.utc) - ca.astimezone(timezone.utc)).total_seconds()
        else:
            c_naive = ca.replace(tzinfo=None) if isinstance(ca, datetime) and ca.tzinfo else ca
            elapsed = (datetime.utcnow() - c_naive).total_seconds()
    except Exception:
        elapsed = 0
    elapsed = max(0.0, float(elapsed))
    base = 78.0
    step = _job_progress_step(job.step_key)
    phase_factor = {0: 1.0, 1: 0.85, 2: 0.45, 3: 0.12}.get(step, 0.5)
    return int(max(5, min(120, (base - elapsed) * phase_factor)))


def _execute_generation_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return
        user = db.get(User, job.user_id)
        if user is None:
            job.status = "error"
            job.step_key = "error"
            job.error_message = "User not found"
            db.commit()
            return

        try:
            req = GenerateRequest.model_validate_json(job.request_json)
        except Exception as exc:
            job.status = "error"
            job.step_key = "error"
            job.error_message = f"Invalid job request: {exc}"[:2000]
            db.commit()
            return

        billing = parse_billing_json(job.billing_json)
        if not billing.get("ref"):
            job.status = "error"
            job.step_key = "error"
            job.error_message = "Billing not reserved for this job"
            db.commit()
            return
        variant_count_cap, image_slots_cap = _generation_caps_from_billing(billing)
        req.templateId = req.templateId or "t1"
        tdef = _template_def(req.templateId)
        req.colorScheme = (tdef.get("theme", {}) or {}).get("colorScheme", "light")
        reqs = _template_generation_requirements(req.templateId, req.blockLayout, db, user.id)

        company_profile = _company_profile_for_user(db, user.id)
        session_id = job.session_id

        def bump(step_key: str) -> None:
            job.status = "running"
            job.step_key = step_key
            db.commit()

        bump("text")
        try:
            pack = generate_pack(
                company_profile=company_profile,
                subject=req.subject,
                image_wishes=req.imageWishes,
                cta_link=req.ctaLink,
                color_scheme=req.colorScheme,
                template_id=req.templateId,
                language=(req.language or DEFAULT_LANGUAGE),
                feedback=None,
                variant_count=max(1, min(int(variant_count_cap or 1), max(reqs["body_count"], reqs["cta_count"], reqs["image_count"], 1))),
                need_body=reqs["body_count"] > 0,
                need_cta=reqs["cta_count"] > 0,
                need_image=(
                    billing.get("imagesAllowed", True)
                    and max(0, min(int(image_slots_cap or 0), reqs["image_count"])) > 0
                ),
            )
        except RuntimeError as exc:
            lang = req.language or DEFAULT_LANGUAGE
            if "IMAGE_POLICY_VIOLATION" in str(exc):
                _apply_job_failure(
                    db,
                    job,
                    user.id,
                    billing,
                    FAILURE_CONTENT_POLICY,
                    _image_policy_user_message(lang),
                    lang,
                )
            else:
                _apply_job_failure(db, job, user.id, billing, FAILURE_SERVER, str(exc)[:4000], lang)
            db.commit()
            return
        except Exception as exc:
            _apply_job_failure(
                db,
                job,
                user.id,
                billing,
                FAILURE_SERVER,
                str(exc)[:4000],
                req.language or DEFAULT_LANGUAGE,
            )
            db.commit()
            return

        bump("image")
        try:
            result = _result_with_layout(
                to_generation_result(
                    session_id=session_id,
                    template_id=req.templateId,
                    pack=pack,
                    cta_link=req.ctaLink,
                    subject=req.subject,
                    color_scheme=req.colorScheme,
                    language=req.language or DEFAULT_LANGUAGE,
                    image_option_count=max(0, min(int(image_slots_cap or 0), reqs["image_count"])),
                    text_option_count=reqs["body_count"],
                    cta_option_count=reqs["cta_count"],
                ),
                req.templateId,
                req.blockLayout,
            )
            result = _attach_block_content(
                result,
                template_id=req.templateId,
                block_layout=req.blockLayout,
                company_profile=company_profile,
                subject=req.subject,
                body_html=(pack.variants[0].body_html if pack.variants else ""),
                language=req.language or DEFAULT_LANGUAGE,
            )
        except RuntimeError as exc:
            lang = req.language or DEFAULT_LANGUAGE
            if "IMAGE_POLICY_VIOLATION" in str(exc):
                _apply_job_failure(
                    db,
                    job,
                    user.id,
                    billing,
                    FAILURE_CONTENT_POLICY,
                    _image_policy_user_message(lang),
                    lang,
                )
            else:
                _apply_job_failure(db, job, user.id, billing, FAILURE_SERVER, str(exc)[:4000], lang)
            db.commit()
            return
        except Exception as exc:
            _apply_job_failure(
                db,
                job,
                user.id,
                billing,
                FAILURE_SERVER,
                str(exc)[:4000],
                req.language or DEFAULT_LANGUAGE,
            )
            db.commit()
            return

        bump("saving")
        try:
            _persist_generation_bundle(
                db,
                user,
                req,
                session_id,
                result,
            )
        except Exception as exc:
            _apply_job_failure(
                db,
                job,
                user.id,
                billing,
                FAILURE_SERVER,
                str(exc)[:4000],
                req.language or DEFAULT_LANGUAGE,
            )
            db.commit()
            return

        job.status = "done"
        job.step_key = "done"
        job.result_json = result.model_dump_json()
        job.error_message = ""
        db.commit()
    except Exception as exc:
        try:
            job2 = db.get(GenerationJob, job_id)
            if job2:
                billing2 = parse_billing_json(job2.billing_json)
                _apply_job_failure(
                    db,
                    job2,
                    job2.user_id,
                    billing2,
                    FAILURE_SERVER,
                    str(exc)[:4000],
                    DEFAULT_LANGUAGE,
                )
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def _run_generation_job_task(job_id: str) -> None:
    await asyncio.to_thread(_execute_generation_job, job_id)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verification_link(token: str) -> str:
    base = (APP_BASE_URL or "").rstrip("/")
    return f"{base}/verify-email.html?token={token}"


def _send_verification_email(email: str, token: str) -> None:
    from_email, from_name = email_dispatch.system_sender()
    if not from_email:
        raise HTTPException(status_code=500, detail="Email provider sender is not configured")
    verify_url = _verification_link(token)
    text = (
        "Welcome to smart-letters.\n\n"
        "Please verify your email by opening this link:\n"
        f"{verify_url}\n\n"
        f"This link expires in {VERIFY_EMAIL_TTL_MINUTES} minutes."
    )
    html = (
        "<p>Welcome to smart-letters.</p>"
        "<p>Please verify your email by clicking the link below:</p>"
        f'<p><a href="{verify_url}">Verify email</a></p>'
        f"<p>This link expires in {VERIFY_EMAIL_TTL_MINUTES} minutes.</p>"
    )
    email_dispatch.send_email(
        from_email=from_email,
        from_name=from_name,
        to_email=email,
        subject="Verify your email address",
        html=html,
        text=text,
    )


def _issue_verification_token(db: Session, user: User) -> str:
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None),
    ).delete()
    token = secrets.token_urlsafe(32)
    row = EmailVerificationToken(
        user_id=user.id,
        token_hash=_token_hash(token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=VERIFY_EMAIL_TTL_MINUTES),
        used_at=None,
    )
    db.add(row)
    db.commit()
    return token


def _paypal_base_url() -> str:
    return "https://api-m.paypal.com" if PAYPAL_ENV == "live" else "https://api-m.sandbox.paypal.com"


def _paypal_access_token() -> str:
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="PayPal is not configured")
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode("utf-8")).decode("ascii")
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            f"{_paypal_base_url()}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal auth failed: {res.status_code}")
    return (res.json() or {}).get("access_token", "")


security = HTTPBearer(auto_error=False)


def _make_user_session(db: Session, user: User, request: Request) -> UserSession:
    ua = (request.headers.get("user-agent", "") or "")[:1000]
    ip = ((request.client.host if request.client else "") or "")[:64]
    # Prevent duplicate session rows for the same device fingerprint.
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.user_agent == ua,
        UserSession.ip_address == ip,
    ).delete()
    sess = UserSession(
        id=uuid.uuid4().hex,
        user_id=user.id,
        user_agent=ua,
        ip_address=ip,
        is_active=True,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = credentials.credentials
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id, session_id = token_data
    db_session = db.get(UserSession, session_id)
    if not db_session or db_session.user_id != user_id or not db_session.is_active:
        raise HTTPException(status_code=401, detail="Session expired")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ----------------------------
# API endpoints (used by frontend/assets/api.js)
# ----------------------------

@app.post("/api/login", response_model=LoginResponse)
def api_login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        if not AUTO_REGISTER_ON_LOGIN:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user = User(email=email, password_hash=hash_password(req.password), email_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if REQUIRE_EMAIL_VERIFICATION and not bool(user.email_verified):
            raise HTTPException(status_code=403, detail="Please verify your email before signing in")

    sess = _make_user_session(db, user, request)
    token = create_access_token(user.id, sess.id)
    return LoginResponse(token=token, user={"id": str(user.id), "email": user.email})


@app.post("/api/register", response_model=LoginResponse, status_code=201)
def api_register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """
    Explicit registration endpoint.
    - Fails if a user with this email already exists.
    - On success, creates a new user and returns a token (same as login).
    """
    email = req.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
    if REQUIRE_LEGAL_CONSENT_AT_REGISTER and not req.legalConsentAccepted:
        raise HTTPException(status_code=400, detail="You must accept Terms and Privacy Policy")

    user = User(
        email=email,
        password_hash=hash_password(req.password),
        email_verified=not REQUIRE_EMAIL_VERIFICATION,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    profile = db.get(UserProfile, user.id)
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    settings = {}
    try:
        settings = json.loads(profile.settings_json or "{}")
    except Exception:
        settings = {}
    settings["legalConsentAccepted"] = bool(req.legalConsentAccepted)
    settings["legalConsentAcceptedAt"] = datetime.now(timezone.utc).isoformat()
    profile.settings_json = json.dumps(settings, ensure_ascii=False)
    db.commit()

    if REQUIRE_EMAIL_VERIFICATION:
        token = _issue_verification_token(db, user)
        _send_verification_email(user.email, token)
        return LoginResponse(token="", user={"id": str(user.id), "email": user.email})

    sess = _make_user_session(db, user, request)
    access_token = create_access_token(user.id, sess.id)
    return LoginResponse(token=access_token, user={"id": str(user.id), "email": user.email})


@app.get("/api/billing/status")
def api_billing_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = _profile_settings_dict(db, user.id)
    ent = _entitlements_for_user(db, user)
    paid_plans = public_plans(paid_only=True)
    free_plan = public_free_plan()
    active_plan = next((p for p in paid_plans if p.id == ent.activePlanId), None)
    primary = active_plan or (paid_plans[0] if paid_plans else None)
    current_plan_id = ent.activePlanId if ent.hasActiveSubscription else (free_plan.id if free_plan else "free")
    return {
        "tokenBalance": ent.tokenBalance,
        "tokensPerText": ent.tokensPerText,
        "tokensPerImage": ent.tokensPerImage,
        "tokensPerGeneration": ent.tokensPerGeneration,
        "tokensPerRefine": ent.tokensPerRefine,
        "tokenUsdReference": ent.tokenUsdReference,
        "freeGenerationsPerDay": ent.freeGenerationsPerDay,
        "freeGenerationsRemainingToday": ent.freeGenerationsRemainingToday,
        "generationsUsedToday": ent.generationsUsedToday,
        "freePlan": free_plan.model_dump() if free_plan else None,
        "plans": [p.model_dump() for p in paid_plans],
        "primaryPlan": primary.model_dump() if primary else None,
        "currentPlanId": current_plan_id,
        "activePlanId": ent.activePlanId,
        "hasActiveSubscription": ent.hasActiveSubscription,
        "canTopUpTokens": ent.canTopUpTokens,
        "paypalSubscriptionId": settings.get("paypalSubscriptionId", ""),
        "paypalPlanId": settings.get("paypalPlanId", "") or ((primary.paypalPlanId if primary else "") or PAYPAL_PLAN_ID or ""),
        "subscriptionActive": ent.hasActiveSubscription,
        "reputationScore": ent.reputationScore,
        "reputationZone": ent.reputationZone,
        "canGenerate": ent.canGenerate,
        "canGenerateImages": ent.canGenerateImages,
        "refundsAllowed": ent.refundsAllowed,
        "reputationBlockedUntil": ent.reputationBlockedUntil,
    }


@app.get("/api/billing/generation-quote", response_model=GenerationCostQuoteResponse)
def api_billing_generation_quote(
    templateId: str = "t1",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tid = (templateId or "t1").strip() or "t1"
    d = _template_def(tid, db, user.id)
    layout = d.get("blockLayout") if d.get("isModular") else None
    reqs = _template_generation_requirements(tid, layout, db, user.id)
    template_wants_image = reqs["image_count"] > 0
    ent = _entitlements_for_user(db, user)
    include_image = template_wants_image and ent.canGenerateImages
    cost = generation_token_cost(include_image=include_image)
    uses_free = ent.canGenerate and ent.canGenerateFreeToday
    can_afford = ent.canGenerate and (
        uses_free or ent.tokenBalance >= cost.total_tokens
    )
    return GenerationCostQuoteResponse(
        templateId=tid,
        includeImage=include_image,
        templateWantsImage=template_wants_image,
        imagesAllowed=ent.canGenerateImages,
        textTokens=cost.text_tokens,
        imageTokens=cost.image_tokens,
        totalTokens=cost.total_tokens,
        tokenBalance=ent.tokenBalance,
        canAfford=can_afford,
        usesFreeSlot=uses_free,
        canGenerate=ent.canGenerate,
        reputationScore=ent.reputationScore,
        reputationZone=ent.reputationZone,
    )


def _refund_request_item(row: TokenRefundRequest) -> TokenRefundRequestItem:
    ca = row.created_at
    ra = row.resolved_at
    return TokenRefundRequestItem(
        id=row.id,
        jobId=row.job_id,
        tokensRequested=row.tokens_requested,
        failureKind=row.failure_kind or "",
        userMessage=row.user_message or "",
        status=row.status,
        adminNote=row.admin_note or "",
        createdAt=ca.isoformat() if hasattr(ca, "isoformat") and ca else None,
        resolvedAt=ra.isoformat() if hasattr(ra, "isoformat") and ra else None,
    )


@app.get("/api/billing/refund-requests", response_model=list[TokenRefundRequestItem])
def api_list_refund_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(TokenRefundRequest)
        .where(TokenRefundRequest.user_id == user.id)
        .order_by(desc(TokenRefundRequest.created_at))
        .limit(50)
    ).all()
    return [_refund_request_item(r) for r in rows]


@app.post("/api/billing/refund-requests", response_model=TokenRefundRequestItem)
def api_create_refund_request(
    payload: TokenRefundRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.get(GenerationJob, payload.jobId.strip())
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "error":
        raise HTTPException(status_code=409, detail="Only failed generations can be reviewed for refund")
    billing = parse_billing_json(job.billing_json)
    failure_kind = (job.failure_kind or FAILURE_SERVER).strip()
    row = create_refund_request(
        db,
        user_id=user.id,
        job_id=job.id,
        billing=billing,
        failure_kind=failure_kind,
        user_message=payload.message,
    )
    db.commit()
    return _refund_request_item(row)


@app.get("/api/admin/refund-requests", response_model=list[TokenRefundRequestItem])
def api_admin_list_refund_requests(
    request: Request,
    db: Session = Depends(get_db),
    status: str = "pending",
):
    _require_admin(request)
    q = select(TokenRefundRequest).order_by(desc(TokenRefundRequest.created_at)).limit(100)
    st = (status or "").strip().lower()
    if st and st != "all":
        q = q.where(TokenRefundRequest.status == st)
    rows = db.scalars(q).all()
    return [_refund_request_item(r) for r in rows]


@app.patch("/api/admin/refund-requests/{request_id}", response_model=TokenRefundRequestItem)
def api_admin_resolve_refund_request(
    request_id: int,
    payload: AdminRefundResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)
    row = resolve_refund_request(
        db,
        request_id=request_id,
        approve=bool(payload.approve),
        admin_note=payload.adminNote,
    )
    db.commit()
    return _refund_request_item(row)


@app.post("/api/billing/paypal/subscribe")
def api_paypal_subscribe(
    payload: dict | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_id = ""
    if payload and isinstance(payload, dict):
        plan_id = str(payload.get("planId") or "").strip()
    paid_plans = public_plans(paid_only=True)
    plan_public = next((p for p in paid_plans if p.id == plan_id), None) if plan_id else (paid_plans[0] if paid_plans else None)
    plan = plan_by_id(plan_public.id) if plan_public else None
    if not plan or plan_is_free(plan):
        raise HTTPException(status_code=400, detail="Cannot subscribe to the free plan")
    paypal_plan = (plan.get("paypalPlanId") or "").strip() or PAYPAL_PLAN_ID
    if not paypal_plan:
        raise HTTPException(status_code=500, detail="PayPal plan is not configured")
    token = _paypal_access_token()
    body = {
        "plan_id": paypal_plan,
        "custom_id": str(user.id),
        "application_context": {
            "brand_name": "smart-letters",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": f"{APP_BASE_URL.rstrip('/')}/account-settings.html?subscribed=1",
            "cancel_url": f"{APP_BASE_URL.rstrip('/')}/plans.html",
        },
    }
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            f"{_paypal_base_url()}/v1/billing/subscriptions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal create subscription failed: {res.status_code}")
    data = res.json() or {}
    approve_url = ""
    for link in (data.get("links") or []):
        if (link.get("rel") or "").lower() == "approve":
            approve_url = link.get("href") or ""
            break
    return {"subscriptionId": data.get("id", ""), "approveUrl": approve_url}


@app.post("/api/billing/paypal/buy-tokens")
def api_paypal_buy_tokens(
    payload: TokenTopUpRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = _profile_settings_dict(db, user.id)
    ent = _entitlements_for_user(db, user)
    if not ent.canTopUpTokens:
        raise HTTPException(
            status_code=403,
            detail="Subscribe to a plan before buying extra tokens",
        )
    plan = plan_by_id(ent.activePlanId) or plan_by_id(str(settings.get("activePlanId") or ""))
    if not plan:
        raise HTTPException(status_code=400, detail="Active plan not found")
    token_count = int(payload.tokenCount)
    amount_usd = topup_price_usd(token_count, plan)
    if amount_usd < 0.01:
        raise HTTPException(status_code=400, detail="Minimum purchase is $0.01")
    plan_id = str(plan.get("id") or "")
    custom_id = f"topup:{user.id}:{token_count}:{plan_id}"
    token = _paypal_access_token()
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": f"{amount_usd:.2f}",
                },
                "custom_id": custom_id[:127],
                "description": f"{token_count} smart-letters tokens",
            }
        ],
        "application_context": {
            "brand_name": "smart-letters",
            "user_action": "PAY_NOW",
            "return_url": f"{APP_BASE_URL.rstrip('/')}/buy-tokens.html?success=1",
            "cancel_url": f"{APP_BASE_URL.rstrip('/')}/buy-tokens.html?cancel=1",
        },
    }
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            f"{_paypal_base_url()}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal create order failed: {res.status_code}")
    data = res.json() or {}
    approve_url = ""
    for link in data.get("links") or []:
        if (link.get("rel") or "").lower() == "approve":
            approve_url = link.get("href") or ""
            break
    return {
        "orderId": data.get("id", ""),
        "approveUrl": approve_url,
        "tokenCount": token_count,
        "amountUsd": amount_usd,
        "planId": plan_id,
    }


@app.post("/api/billing/paypal/capture-order")
def api_paypal_capture_order(
    payload: dict | None = Body(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order_id = ""
    if payload and isinstance(payload, dict):
        order_id = str(payload.get("orderId") or "").strip()
    if not order_id:
        raise HTTPException(status_code=400, detail="orderId is required")
    token = _paypal_access_token()
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            f"{_paypal_base_url()}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"PayPal capture failed: {res.status_code}")
    data = res.json() or {}
    credited = _fulfill_paypal_order_capture(db, user_id=user.id, order=data)
    db.commit()
    return {"ok": True, "credited": credited, "tokenBalance": get_token_balance(db, user.id)}


def _fulfill_paypal_order_capture(db: Session, *, user_id: int, order: dict) -> bool:
    units = order.get("purchase_units") or []
    if not units:
        return False
    unit = units[0] if isinstance(units[0], dict) else {}
    custom_id = str(unit.get("custom_id") or "").strip()
    parsed = parse_topup_custom_id(custom_id)
    if not parsed:
        return False
    uid, token_count, plan_id = parsed
    if uid != user_id:
        return False
    plan = plan_by_id(plan_id)
    if not plan:
        return False
    amount = unit.get("amount") or {}
    try:
        paid = float(str(amount.get("value") or "0"))
    except (TypeError, ValueError):
        paid = 0.0
    expected = topup_price_usd(token_count, plan)
    if abs(paid - expected) > 0.02:
        return False
    external_id = str(order.get("id") or "").strip()
    if not external_id:
        return False
    amount_cents = int(round(paid * 100))
    return fulfill_token_topup(
        db,
        user_id=user_id,
        token_count=token_count,
        external_id=external_id,
        plan_id=plan_id,
        amount_cents=amount_cents,
    )


@app.post("/api/billing/paypal/webhook")
async def api_paypal_webhook(request: Request, db: Session = Depends(get_db)):
    body_bytes = await request.body()
    event = {}
    try:
        event = json.loads(body_bytes.decode("utf-8") or "{}")
    except Exception:
        event = {}

    # Best-effort signature verification.
    if PAYPAL_WEBHOOK_ID:
        token = _paypal_access_token()
        verify_payload = {
            "transmission_id": request.headers.get("paypal-transmission-id", ""),
            "transmission_time": request.headers.get("paypal-transmission-time", ""),
            "cert_url": request.headers.get("paypal-cert-url", ""),
            "auth_algo": request.headers.get("paypal-auth-algo", ""),
            "transmission_sig": request.headers.get("paypal-transmission-sig", ""),
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": event,
        }
        with httpx.Client(timeout=15.0) as client:
            vr = client.post(
                f"{_paypal_base_url()}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=verify_payload,
            )
        if vr.status_code >= 400 or (vr.json() or {}).get("verification_status") != "SUCCESS":
            raise HTTPException(status_code=400, detail="Invalid PayPal webhook signature")

    et = (event.get("event_type") or "").strip()
    resource = event.get("resource") or {}
    if not isinstance(resource, dict):
        resource = {}

    custom_id = str(resource.get("custom_id") or "").strip()
    if not custom_id:
        sub = resource.get("subscriber") or {}
        if isinstance(sub, dict):
            custom_id = str(sub.get("custom_id") or "").strip()
    if not custom_id:
        return {"ok": True}
    try:
        uid = int(custom_id)
    except Exception:
        return {"ok": True}
    user = db.get(User, uid)
    if not user:
        return {"ok": True}

    plan_id = ""
    if et.startswith("BILLING.SUBSCRIPTION"):
        plan_id = str(resource.get("plan_id") or "").strip()
    elif et == "PAYMENT.SALE.COMPLETED":
        plan_id = str(resource.get("billing_plan_id") or resource.get("plan_id") or "").strip()

    if et in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        units = resource.get("purchase_units") or []
        if units and isinstance(units[0], dict):
            custom_id = str(units[0].get("custom_id") or "").strip()
            parsed = parse_topup_custom_id(custom_id)
            if parsed:
                uid, token_count, topup_plan_id = parsed
                if uid == user.id:
                    plan = plan_by_id(topup_plan_id)
                    if plan:
                        amount = (units[0].get("amount") or {}) if isinstance(units[0], dict) else {}
                        try:
                            paid = float(str(amount.get("value") or "0"))
                        except (TypeError, ValueError):
                            paid = 0.0
                        if abs(paid - topup_price_usd(token_count, plan)) <= 0.02:
                            ext = str(resource.get("id") or order_id_from_resource(resource) or "").strip()
                            if ext:
                                fulfill_token_topup(
                                    db,
                                    user_id=user.id,
                                    token_count=token_count,
                                    external_id=ext,
                                    plan_id=topup_plan_id,
                                    amount_cents=int(round(paid * 100)),
                                )
        db.commit()
        return {"ok": True}

    fulfill_paypal_payment(
        db,
        user_id=user.id,
        event_type=et,
        resource=resource,
        paypal_plan_id=plan_id,
    )

    if et.startswith("BILLING.SUBSCRIPTION"):
        settings = _profile_settings_dict(db, user.id)
        sub_id = str(resource.get("id") or "").strip()
        if sub_id:
            settings["paypalSubscriptionId"] = sub_id
        if plan_id:
            settings["paypalPlanId"] = plan_id
        matched = next(
            (p for p in public_plans(paid_only=True) if (p.paypalPlanId or "").strip() == plan_id),
            None,
        )
        if matched:
            settings["activePlanId"] = matched.id
            activate_subscription_plan(
                db, user_id=user.id, plan_id=matched.id, paypal_plan_id=plan_id
            )
        settings.pop("subscriptionActive", None)
        _write_profile_settings(db, user.id, settings)
    else:
        db.commit()
    return {"ok": True}


def order_id_from_resource(resource: dict) -> str:
    return str(resource.get("id") or resource.get("order_id") or "").strip()


@app.post("/api/send/generated/{email_id}")
def api_send_generated_email(email_id: int, payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GeneratedEmail, email_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generated email not found")
    to_email = str(payload.get("toEmail") or "").strip()
    if not to_email:
        raise HTTPException(status_code=400, detail="toEmail is required")
    company = db.get(CompanyProfile, user.id)
    data = {}
    if company and company.data_json:
        try:
            data = json.loads(company.data_json or "{}")
        except Exception:
            data = {}
    sender_email = str(data.get("senderEmail") or data.get("email") or "").strip()
    sender_name = str(data.get("senderName") or data.get("companyName") or "").strip()
    if not sender_email:
        raise HTTPException(status_code=400, detail="Configure sender email in company profile")
    if not email_dispatch.sender_is_verified(sender_email):
        raise HTTPException(status_code=400, detail="Sender email is not verified with the email provider")
    html = row.html_snapshot or ""
    if not html:
        try:
            payload_data = json.loads(row.payload_json or "{}")
            sid = str(payload_data.get("sessionId") or "").strip()
            if sid:
                exp = api_export(ExportRequest(session_id=sid, image_index=0, text_index=0, cta_index=0), user, db)
                html = str((exp or {}).get("html") or "")
        except Exception:
            html = ""
    if not html:
        raise HTTPException(status_code=400, detail="No rendered email HTML available")
    email_dispatch.send_email(
        from_email=sender_email,
        from_name=sender_name or sender_email,
        to_email=to_email,
        subject=row.subject or "smart-letters message",
        html=html,
    )
    row.html_snapshot = html
    db.commit()
    return {"ok": True}


@app.get("/api/account/export")
def api_export_account_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(UserProfile, user.id)
    company = db.get(CompanyProfile, user.id)
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user.id)).all()
    generated = db.scalars(select(GeneratedEmail).where(GeneratedEmail.user_id == user.id)).all()
    profile_settings = {}
    if profile and profile.settings_json:
        try:
            profile_settings = json.loads(profile.settings_json)
        except Exception:
            profile_settings = {}
    company_profile = {}
    if company and company.data_json:
        try:
            company_profile = json.loads(company.data_json)
        except Exception:
            company_profile = {}
    generated_emails_out = []
    for g in generated:
        payload_data = {}
        if g.payload_json:
            try:
                payload_data = json.loads(g.payload_json)
            except Exception:
                payload_data = {}
        generated_emails_out.append(
            {
                "id": g.id,
                "title": g.title,
                "subject": g.subject,
                "templateId": g.template_id,
                "payload": payload_data if isinstance(payload_data, dict) else {},
                "htmlSnapshot": g.html_snapshot,
                "createdAt": (g.created_at.isoformat() if g.created_at else None),
                "updatedAt": (g.updated_at.isoformat() if g.updated_at else None),
            }
        )
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "createdAt": (user.created_at.isoformat() if user.created_at else None),
        },
        "profile": {
            "displayName": (profile.display_name if profile else ""),
            "avatarUrl": (profile.avatar_url if profile else ""),
            "settings": profile_settings,
        },
        "companyProfile": company_profile,
        "sessions": [
            {
                "id": s.id,
                "userAgent": s.user_agent,
                "ipAddress": s.ip_address,
                "isActive": s.is_active,
                "createdAt": (s.created_at.isoformat() if s.created_at else None),
                "lastSeenAt": (s.last_seen_at.isoformat() if s.last_seen_at else None),
            }
            for s in sessions
        ],
        "generatedEmails": generated_emails_out,
    }


@app.get("/api/auth/verify-email")
def api_verify_email(token: str, db: Session = Depends(get_db)):
    token_hash = _token_hash(token or "")
    row = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash))
    if not row:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if row.used_at is not None:
        raise HTTPException(status_code=400, detail="Verification token has already been used")
    now = datetime.now(timezone.utc)
    exp = row.expires_at
    # SQLite returns naive datetimes; treat a missing tzinfo as UTC so the comparison
    # below never mixes naive and aware values (TypeError).
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp is None or exp < now:
        raise HTTPException(status_code=400, detail="Verification token has expired")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email_verified = True
    row.used_at = now
    db.commit()
    return {"ok": True, "message": "Email verified successfully"}


@app.post("/api/auth/resend-verification")
def api_resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    if not REQUIRE_EMAIL_VERIFICATION:
        return {"ok": True, "message": "Email verification is not required."}
    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)
    last = _RESEND_RATE_LIMIT.get(email)
    if last and (now - last).total_seconds() < 60:
        return {"ok": True, "message": "Please wait before requesting another verification email."}
    user = db.scalar(select(User).where(User.email == email))
    # Do not disclose user existence/state details.
    if not user:
        return {"ok": True, "message": "If this email exists, a verification email has been sent."}
    if user.email_verified:
        return {"ok": True, "message": "This email is already verified. You can sign in."}
    token = _issue_verification_token(db, user)
    _send_verification_email(email, token)
    _RESEND_RATE_LIMIT[email] = now
    return {"ok": True, "message": "Verification email sent."}


## Custom template system removed.


@app.get("/api/account", response_model=AccountSettingsResponse)
def api_get_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(UserProfile, user.id)
    settings = {}
    if profile and profile.settings_json:
        try:
            settings = json.loads(profile.settings_json)
        except Exception:
            settings = {}
    return AccountSettingsResponse(
        email=user.email,
        displayName=(profile.display_name if profile else ""),
        avatarUrl=(profile.avatar_url if profile else ""),
        settings=settings,
        entitlements=_entitlements_for_user(db, user),
    )


@app.patch("/api/account", response_model=AccountSettingsResponse)
def api_update_account(payload: AccountSettingsUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower().strip())) if payload.email else None
    if existing_user and existing_user.id != user.id:
        raise HTTPException(status_code=409, detail="Email already in use")
    if payload.email:
        user.email = payload.email.lower().strip()

    profile = db.get(UserProfile, user.id)
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    if payload.displayName is not None:
        profile.display_name = payload.displayName
    if payload.avatarUrl is not None:
        profile.avatar_url = payload.avatarUrl
    if payload.settings is not None:
        prev = {}
        if profile.settings_json:
            try:
                prev = json.loads(profile.settings_json)
            except Exception:
                prev = {}
        merged = {
            **prev,
            **{
                k: v
                for k, v in payload.settings.items()
                if k not in PROTECTED_PROFILE_SETTINGS_KEYS
            },
        }
        merged.pop("subscriptionActive", None)
        merged.pop("demoAdmin", None)
        profile.settings_json = json.dumps(merged, ensure_ascii=False)
    db.commit()

    settings = {}
    try:
        settings = json.loads(profile.settings_json or "{}")
    except Exception:
        settings = {}
    return AccountSettingsResponse(
        email=user.email,
        displayName=profile.display_name,
        avatarUrl=profile.avatar_url,
        settings=settings,
        entitlements=_entitlements_for_user(db, user),
    )


@app.patch("/api/account/password")
def api_change_password(payload: PasswordUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.currentPassword, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(payload.newPassword)
    db.commit()
    return {"ok": True}


@app.get("/api/account/sessions", response_model=list[UserSessionItem])
def api_list_sessions(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    current_sid = None
    if credentials is not None:
        td = decode_token(credentials.credentials)
        if td is not None:
            _uid, current_sid = td
    rows = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.is_active.is_(True))
        .order_by(desc(UserSession.created_at))
    ).all()
    return [
        UserSessionItem(
            id=r.id,
            userAgent=r.user_agent,
            ipAddress=r.ip_address,
            isActive=r.is_active,
            isCurrent=(r.id == current_sid),
            createdAt=(r.created_at.isoformat() if r.created_at else None),
            lastSeenAt=(r.last_seen_at.isoformat() if r.last_seen_at else None),
        )
        for r in rows
    ]


@app.delete("/api/account/sessions/{session_id}")
def api_revoke_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UserSession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.delete("/api/account/sessions/current")
def api_revoke_current_session(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    td = decode_token(credentials.credentials)
    if td is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    _uid, sid = td
    row = db.get(UserSession, sid)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.delete("/api/account")
def api_delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.query(GeneratedEmail).filter(GeneratedEmail.user_id == user.id).delete()
    db.query(GenerationLog).filter(GenerationLog.user_id == user.id).delete()
    db.query(GenerationSession).filter(GenerationSession.user_id == user.id).delete()
    db.query(CompanyProfile).filter(CompanyProfile.user_id == user.id).delete()
    db.query(UserProfile).filter(UserProfile.user_id == user.id).delete()
    db.delete(user)
    db.commit()
    return {"ok": True}

@app.get("/api/company", response_model=CompanyProfileSchema)
def api_get_company(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CompanyProfile, user.id)
    if not row:
        return CompanyProfileSchema()
    try:
        data = json.loads(row.data_json or "{}")
    except Exception:
        data = {}
    return CompanyProfileSchema(**data)

@app.put("/api/company", response_model=CompanyProfileSchema)
def api_update_company(payload: CompanyProfileSchema, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CompanyProfile, user.id)
    old: dict = {}
    if row and row.data_json:
        try:
            old = json.loads(row.data_json)
        except Exception:
            old = {}
    data = payload.model_dump()
    # senderVerified is server-authoritative: never trust the client value, otherwise it
    # would be reset to False on every profile save. Re-check live with the provider; on
    # error keep the previous flag only when the sender email is unchanged.
    sender_email = str(data.get("senderEmail") or "").strip()
    if sender_email:
        try:
            data["senderVerified"] = bool(email_dispatch.sender_is_verified(sender_email))
        except Exception:
            same = sender_email.lower() == str(old.get("senderEmail") or "").strip().lower()
            data["senderVerified"] = bool(old.get("senderVerified")) and same
    else:
        data["senderVerified"] = False
    if not row:
        row = CompanyProfile(user_id=user.id, data_json=json.dumps(data, ensure_ascii=False))
        db.add(row)
    else:
        row.data_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    return CompanyProfileSchema(**data)


@app.post("/api/company/verify-sender")
def api_verify_company_sender(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CompanyProfile, user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Company profile not found")
    try:
        data = json.loads(row.data_json or "{}")
    except Exception:
        data = {}
    sender_email = str(data.get("senderEmail") or "").strip()
    if not sender_email:
        raise HTTPException(status_code=400, detail="senderEmail is required")
    verified = email_dispatch.sender_is_verified(sender_email)
    data["senderVerified"] = bool(verified)
    row.data_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    return {"ok": True, "senderVerified": bool(verified)}

@app.post("/api/logo")
async def api_upload_logo(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """
    Accept a logo image and store it.
    If Cloudflare R2 is configured, upload there and return a public URL.
    Otherwise, return a data: URI fallback as before.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    mime = file.content_type or "image/png"

    # Try to store in R2 first
    try:
        r2_url = upload_image_bytes_to_r2(content, key_prefix="logos", content_type=mime)
    except Exception:
        r2_url = None

    if r2_url:
        return {"url": r2_url}

    # Fallback: inline data URI (previous behavior)
    b64 = base64.b64encode(content).decode("ascii")
    return {"url": f"data:{mime};base64,{b64}"}


@app.post("/api/avatar")
async def api_upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """
    Profile picture upload (same storage behavior as company logo).
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    mime = file.content_type or "image/png"

    try:
        r2_url = upload_image_bytes_to_r2(content, key_prefix="avatars", content_type=mime)
    except Exception:
        r2_url = None

    if r2_url:
        return {"url": r2_url}

    b64 = base64.b64encode(content).decode("ascii")
    return {"url": f"data:{mime};base64,{b64}"}


@app.get("/api/templates", response_model=list[TemplateItem])
def api_templates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out = []
    for tid, d in BUILTIN_TEMPLATE_DEFS.items():
        layout = d.get("blockLayout") or []
        out.append(
            {
                "id": tid,
                "name": d["name"],
                "previewImageUrl": d["previewImageUrl"],
                "objectCounts": _object_counts_for_template(tid, layout if d.get("isModular") else None),
                "theme": d.get("theme", {}),
                "isModular": bool(d.get("isModular")),
                "blockLayout": layout if d.get("isModular") else [],
                "isBuiltin": True,
                "userTemplateId": None,
            }
        )
    rows = db.scalars(
        select(UserTemplate)
        .where(UserTemplate.user_id == user.id)
        .order_by(desc(UserTemplate.updated_at))
    ).all()
    for row in rows:
        out.append(_user_template_to_item(row))
    return out


@app.get("/api/user-templates", response_model=list[UserTemplateItem])
def api_user_templates_list(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(UserTemplate)
        .where(UserTemplate.user_id == user.id)
        .order_by(desc(UserTemplate.updated_at))
    ).all()
    items = []
    for row in rows:
        item = _user_template_to_item(row)
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "baseTemplateId": row.base_template_id,
                "isModular": bool(row.is_modular),
                "blockLayout": item.get("blockLayout") or [],
                "theme": item.get("theme") or {},
                "updatedAt": item.get("updatedAt"),
            }
        )
    return items


@app.post("/api/user-templates", response_model=UserTemplateItem, status_code=201)
def api_user_templates_create(
    req: UserTemplateCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        name = sanitize_template_name(req.name)
        layout = validate_block_layout(req.blockLayout or [])
        theme = sanitize_theme(req.theme)
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    saved_count = db.scalar(
        select(func.count()).select_from(UserTemplate).where(UserTemplate.user_id == user.id)
    ) or 0
    if saved_count >= MAX_USER_TEMPLATES_PER_USER:
        raise HTTPException(status_code=400, detail="Template limit reached")
    row = UserTemplate(
        user_id=user.id,
        name=name,
        base_template_id=(req.baseTemplateId or "custom").strip() or "custom",
        is_modular=bool(req.isModular),
        layout_json=json.dumps(layout, ensure_ascii=False),
        theme_json=json.dumps(theme, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    item = _user_template_to_item(row)
    return {
        "id": row.id,
        "name": row.name,
        "baseTemplateId": row.base_template_id,
        "isModular": bool(row.is_modular),
        "blockLayout": item.get("blockLayout") or [],
        "theme": item.get("theme") or {},
        "updatedAt": item.get("updatedAt"),
    }


@app.get("/api/user-templates/{template_id}", response_model=UserTemplateItem)
def api_user_templates_get(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(UserTemplate, template_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    item = _user_template_to_item(row)
    return {
        "id": row.id,
        "name": row.name,
        "baseTemplateId": row.base_template_id,
        "isModular": bool(row.is_modular),
        "blockLayout": item.get("blockLayout") or [],
        "theme": item.get("theme") or {},
        "updatedAt": item.get("updatedAt"),
    }


@app.put("/api/user-templates/{template_id}", response_model=UserTemplateItem)
def api_user_templates_update(
    template_id: int,
    req: UserTemplateUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(UserTemplate, template_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        if req.name is not None:
            row.name = sanitize_template_name(req.name)
        if req.blockLayout is not None:
            row.layout_json = json.dumps(validate_block_layout(req.blockLayout), ensure_ascii=False)
        if req.theme is not None:
            row.theme_json = json.dumps(sanitize_theme(req.theme), ensure_ascii=False)
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(row)
    item = _user_template_to_item(row)
    return {
        "id": row.id,
        "name": row.name,
        "baseTemplateId": row.base_template_id,
        "isModular": bool(row.is_modular),
        "blockLayout": item.get("blockLayout") or [],
        "theme": item.get("theme") or {},
        "updatedAt": item.get("updatedAt"),
    }


@app.delete("/api/user-templates/{template_id}")
def api_user_templates_delete(
    template_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(UserTemplate, template_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/blocks")
def api_blocks(lang: str | None = None, user: User = Depends(get_current_user)):
    return localized_blocks(lang)


@app.post("/api/templates/render-preview")
def api_render_preview(
    req: RenderPreviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prof = db.get(CompanyProfile, user.id)
    company_profile = {}
    if prof and prof.data_json:
        try:
            company_profile = json.loads(prof.data_json)
        except Exception:
            company_profile = {}
    try:
        block_layout = validate_block_layout(
            [{"name": b.name, "context": b.context or {}} for b in req.blockLayout]
        )
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    html = render_modular_email(
        block_layout,
        company_profile=company_profile,
        subject=sanitize_preview_subject(req.subject or ""),
        body_html=sanitize_preview_body_html(req.bodyHtml or ""),
        image_url=sanitize_url(req.imageUrl) if req.imageUrl else None,
        cta_link=sanitize_url(req.ctaLink) if req.ctaLink else None,
        cta_label=sanitize_string(req.ctaLabel) if req.ctaLabel else None,
        theme=sanitize_theme(req.theme or {}),
    )
    return {"html": html}

@app.post("/api/generate/start", response_model=GenerateJobStarted)
async def api_generate_start(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not llm_is_configured():
        raise HTTPException(status_code=500, detail="LLM provider is not configured")
    req.templateId = req.templateId or "t1"
    _apply_user_template_to_request(db, user.id, req)
    _validate_generate_block_layout(req)
    req.colorScheme = (_template_def(req.templateId, db, user.id).get("theme", {}) or {}).get(
        "colorScheme", "light"
    )
    reqs = _template_generation_requirements(req.templateId, req.blockLayout, db, user.id)
    include_image = reqs["image_count"] > 0
    job_id = uuid.uuid4().hex
    billing = charge_for_generation(
        db,
        user_id=user.id,
        ref_id=job_id,
        lang=req.language or DEFAULT_LANGUAGE,
        include_image=include_image,
    )
    session_id = f"sess_{uuid.uuid4().hex[:24]}"
    job = GenerationJob(
        id=job_id,
        user_id=user.id,
        status="queued",
        step_key="queued",
        error_message="",
        request_json=req.model_dump_json(),
        session_id=session_id,
        result_json=None,
        billing_json=billing_json(
            billing.mode,
            billing.tokens_charged,
            job_id,
            text_tokens=billing.text_tokens_charged,
            image_tokens=billing.image_tokens_charged,
            images_allowed=billing.images_allowed,
        ),
    )
    db.add(job)
    db.commit()
    background_tasks.add_task(_run_generation_job_task, job_id)
    return GenerateJobStarted(jobId=job_id, sessionId=session_id)


@app.get("/api/generate/job/{job_id}/result", response_model=GenerationResult)
def api_generate_job_result(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return saved generation when the job finished (for opening compose)."""
    job = db.get(GenerationJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done" or not job.result_json:
        raise HTTPException(status_code=409, detail="Generation is not ready yet")
    try:
        return GenerationResult.model_validate_json(job.result_json)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Invalid stored result") from exc


@app.get("/api/generate/jobs", response_model=list[GenerateJobListItem])
def api_generate_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    lim = max(1, min(int(limit or 100), 200))
    rows = db.scalars(
        select(GenerationJob)
        .where(GenerationJob.user_id == user.id)
        .order_by(desc(GenerationJob.created_at))
        .limit(lim)
    ).all()
    out: list[GenerateJobListItem] = []
    for job in rows:
        subj, tmpl = "", ""
        try:
            req = GenerateRequest.model_validate_json(job.request_json)
            subj = (req.subject or "")[:240]
            tmpl = req.templateId or ""
        except Exception:
            pass
        err_preview = None
        if job.status == "error" and (job.error_message or "").strip():
            err_preview = (job.error_message or "")[:240]
        est = _job_estimate_remaining_seconds(job)
        billing = parse_billing_json(job.billing_json)
        fk = (job.failure_kind or "").strip() or None
        charged = int(billing.get("tokensCharged") or 0)
        rstat = job_refund_status(db, user.id, job.id, billing) if job.status == "error" else "none"
        out.append(
            GenerateJobListItem(
                jobId=job.id,
                sessionId=job.session_id,
                status=job.status,
                stepKey=job.step_key,
                progressStep=_job_progress_step(job.step_key),
                totalSteps=3,
                startedAt=_job_started_at_iso(job),
                subject=subj,
                templateId=tmpl,
                error=err_preview,
                estimatedSecondsRemaining=est,
                failureKind=fk,
                tokensCharged=charged,
                refundStatus=rstat,
                canRequestRefund=(
                    job.status == "error"
                    and can_request_refund(db, user.id, job.id, billing, fk or FAILURE_SERVER)
                ),
            )
        )
    return out


@app.post("/api/generate/job/{job_id}/retry", response_model=GenerateJobStarted)
async def api_generate_job_retry(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    src = db.get(GenerationJob, job_id)
    if src is None or src.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if src.status != "error":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
    try:
        req = GenerateRequest.model_validate_json(src.request_json)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid stored job request") from exc
    new_job_id = uuid.uuid4().hex
    _apply_user_template_to_request(db, user.id, req)
    reqs = _template_generation_requirements(req.templateId, req.blockLayout, db, user.id)
    include_image = reqs["image_count"] > 0
    billing = charge_for_generation(
        db,
        user_id=user.id,
        ref_id=new_job_id,
        lang=req.language or DEFAULT_LANGUAGE,
        include_image=include_image,
    )
    new_session_id = f"sess_{uuid.uuid4().hex[:24]}"
    cloned = GenerationJob(
        id=new_job_id,
        user_id=user.id,
        status="queued",
        step_key="queued",
        error_message="",
        request_json=src.request_json,
        session_id=new_session_id,
        result_json=None,
        billing_json=billing_json(
            billing.mode,
            billing.tokens_charged,
            new_job_id,
            text_tokens=billing.text_tokens_charged,
            image_tokens=billing.image_tokens_charged,
            images_allowed=billing.images_allowed,
        ),
    )
    db.add(cloned)
    db.commit()
    background_tasks.add_task(_run_generation_job_task, new_job_id)
    return GenerateJobStarted(jobId=new_job_id, sessionId=new_session_id)


@app.delete("/api/generate/job/{job_id}")
def api_generate_job_delete(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GenerationJob, job_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if row.status not in ("error", "done"):
        raise HTTPException(status_code=409, detail="Only finished jobs can be removed")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.post("/api/generate", response_model=GenerationResult)
def api_generate(req: GenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not llm_is_configured():
        raise HTTPException(status_code=500, detail="LLM provider is not configured")
    req.templateId = req.templateId or "t1"
    _apply_user_template_to_request(db, user.id, req)
    _validate_generate_block_layout(req)
    tdef = _template_def(req.templateId, db, user.id)
    req.colorScheme = (tdef.get("theme", {}) or {}).get("colorScheme", "light")

    reqs = _template_generation_requirements(req.templateId, req.blockLayout, db, user.id)
    include_image = reqs["image_count"] > 0
    sync_ref = f"sync_{uuid.uuid4().hex}"
    billing_charge = charge_for_generation(
        db,
        user_id=user.id,
        ref_id=sync_ref,
        lang=req.language or DEFAULT_LANGUAGE,
        include_image=include_image,
    )
    billing = {
        "mode": billing_charge.mode,
        "tokensCharged": billing_charge.tokens_charged,
        "textTokens": billing_charge.text_tokens_charged,
        "imageTokens": billing_charge.image_tokens_charged,
        "imagesAllowed": billing_charge.images_allowed,
        "ref": sync_ref,
    }
    variant_count_cap, image_slots_cap = billing_charge.variant_count, billing_charge.image_slots
    company_profile = _company_profile_for_user(db, user.id)
    session_id = f"sess_{uuid.uuid4().hex[:24]}"
    try:
        result = _result_with_layout(
            _call_pack_and_result(
                company_profile=company_profile,
                req=req,
                session_id=session_id,
                variant_count_cap=variant_count_cap,
                image_slots_cap=image_slots_cap,
                requirements=reqs,
                images_allowed=billing_charge.images_allowed,
            ),
            req.templateId,
            req.blockLayout,
        )
    except RuntimeError as exc:
        lang = req.language or DEFAULT_LANGUAGE
        if "IMAGE_POLICY_VIOLATION" in str(exc):
            msg = handle_generation_failure(
                db,
                user_id=user.id,
                billing=billing,
                failure_kind=FAILURE_CONTENT_POLICY,
                lang=lang,
            )
            db.commit()
            raise HTTPException(status_code=400, detail=msg or _image_policy_user_message(lang))
        handle_generation_failure(
            db, user_id=user.id, billing=billing, failure_kind=FAILURE_SERVER, lang=lang
        )
        db.commit()
        raise
    except Exception:
        handle_generation_failure(
            db,
            user_id=user.id,
            billing=billing,
            failure_kind=FAILURE_SERVER,
            lang=req.language or DEFAULT_LANGUAGE,
        )
        db.commit()
        raise

    result = _attach_block_content(
        result,
        template_id=req.templateId,
        block_layout=req.blockLayout,
        company_profile=company_profile,
        subject=req.subject,
        body_html=(result.textOptions[0].html if result.textOptions else ""),
        language=req.language or DEFAULT_LANGUAGE,
    )

    _persist_generation_bundle(db, user, req, session_id, result)
    return result

@app.post("/api/refine", response_model=GenerationResult)
def api_refine(req: RefineRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not llm_is_configured():
        raise HTTPException(status_code=500, detail="LLM provider is not configured")

    refine_ref = f"refine_{uuid.uuid4().hex}"
    has_text = bool((req.textFeedback or "").strip() or (req.ctaFeedback or "").strip())
    has_image = bool((req.imageFeedback or "").strip())
    billing_charge = charge_for_refine(
        db,
        user_id=user.id,
        ref_id=refine_ref,
        lang=req.language or DEFAULT_LANGUAGE,
        refine_text=has_text,
        refine_image=has_image,
    )
    billing = {
        "mode": billing_charge.mode,
        "tokensCharged": billing_charge.tokens_charged,
        "textTokens": billing_charge.text_tokens_charged,
        "imageTokens": billing_charge.image_tokens_charged,
        "ref": refine_ref,
    }

    session_id = req.sessionId or f"sess_{uuid.uuid4().hex[:24]}"

    existing = db.get(GenerationSession, session_id)
    if existing and existing.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    base_generation = None
    if existing:
        try:
            base_generation = json.loads(existing.generation_json)
        except Exception:
            base_generation = None

    prof = db.get(CompanyProfile, user.id)
    company_profile = {}
    if prof and prof.data_json:
        try:
            company_profile = json.loads(prof.data_json)
        except Exception:
            company_profile = {}

    feedback = {
        "imageFeedback": req.imageFeedback,
        "textFeedback": req.textFeedback,
        "ctaFeedback": req.ctaFeedback,
        "base_generation": base_generation,
    }

    # We reuse prior templateId when possible
    template_id = req.templateId or (base_generation.get("templateId") if isinstance(base_generation, dict) else None) or "t1"

    # Keep href from previous generation if available
    cta_link = ""
    if isinstance(base_generation, dict):
        try:
            cta_link = base_generation.get("ctaOptions", [{}])[0].get("href", "")
        except Exception:
            cta_link = ""

    refine_variants = billing_charge.variant_count
    refine_image_slots = billing_charge.image_slots

    try:
        pack = generate_pack(
            company_profile=company_profile,
            subject="(refine)",  # subject is not used by UI after first step; keep short
            image_wishes="",
            cta_link="",
            color_scheme="",
            template_id=template_id,
            language=(req.language or DEFAULT_LANGUAGE),
            feedback=feedback,
            variant_count=refine_variants,
        )
    except RuntimeError as exc:
        lang = req.language or DEFAULT_LANGUAGE
        if "IMAGE_POLICY_VIOLATION" in str(exc):
            msg = handle_generation_failure(
                db,
                user_id=user.id,
                billing=billing,
                failure_kind=FAILURE_CONTENT_POLICY,
                lang=lang,
            )
            db.commit()
            raise HTTPException(status_code=400, detail=msg or _image_policy_user_message(lang))
        handle_generation_failure(
            db, user_id=user.id, billing=billing, failure_kind=FAILURE_SERVER, lang=lang
        )
        db.commit()
        raise
    except Exception:
        handle_generation_failure(
            db,
            user_id=user.id,
            billing=billing,
            failure_kind=FAILURE_SERVER,
            lang=req.language or DEFAULT_LANGUAGE,
        )
        db.commit()
        raise

    result = to_generation_result(
        session_id=session_id,
        template_id=template_id,
        pack=pack,
        cta_link=cta_link,
        subject=base_generation.get("subject", "") if isinstance(base_generation, dict) else "",
        color_scheme=base_generation.get("colorScheme", "") if isinstance(base_generation, dict) else "",
        language=req.language or DEFAULT_LANGUAGE,
        image_option_count=refine_image_slots,
    )

    if existing:
        existing.generation_json = result.model_dump_json()
        if existing.generated_email_id:
            gen_row = db.get(GeneratedEmail, existing.generated_email_id)
            if gen_row and gen_row.user_id == user.id:
                gen_row.payload_json = result.model_dump_json()
                gen_row.subject = result.subject or gen_row.subject
                gen_row.template_id = result.templateId or gen_row.template_id
    else:
        generated = GeneratedEmail(
            user_id=user.id,
            title="Refined email",
            subject=result.subject or "",
            template_id=result.templateId,
            payload_json=result.model_dump_json(),
            html_snapshot="",
        )
        db.add(generated)
        db.flush()
        db.add(
            GenerationSession(
                session_id=session_id,
                user_id=user.id,
                generation_json=result.model_dump_json(),
                generated_email_id=generated.id,
            )
        )
    db.commit()
    return result


@app.put("/api/generation-session/{session_id}", response_model=GenerationResult)
def api_put_generation_session(
    session_id: str,
    payload: GenerationResult,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Persist the current generation JSON (e.g. user-edited email body in compose).
    Keeps export and refine in sync with the latest client-side state.
    """
    row = db.get(GenerationSession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    merged = payload.model_dump()
    merged["sessionId"] = session_id
    fixed = GenerationResult.model_validate(merged)
    row.generation_json = fixed.model_dump_json()
    if row.generated_email_id:
        ge = db.get(GeneratedEmail, row.generated_email_id)
        if ge and ge.user_id == user.id:
            ge.payload_json = row.generation_json
            if fixed.subject:
                ge.subject = fixed.subject
    db.commit()
    return fixed


@app.get("/api/generated-emails", response_model=list[GeneratedEmailListItem])
def api_generated_emails(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(GeneratedEmail).where(GeneratedEmail.user_id == user.id).order_by(desc(GeneratedEmail.updated_at))
    ).all()
    items: list[GeneratedEmailListItem] = []
    for r in rows:
        tags = []
        try:
            tags = json.loads(r.tags_json or "[]")
        except Exception:
            tags = []
        preview = ""
        try:
            payload = json.loads(r.payload_json or "{}")
            txt = (payload.get("textOptions") or [{}])[0].get("html", "")
            preview = txt[:140]
        except Exception:
            preview = ""
        items.append(
            GeneratedEmailListItem(
                id=r.id,
                title=r.title or "",
                subject=r.subject or "",
                templateId=r.template_id or "",
                isFavorite=bool(r.is_favorite),
                tags=tags if isinstance(tags, list) else [],
                createdAt=(r.created_at.isoformat() if r.created_at else None),
                updatedAt=(r.updated_at.isoformat() if r.updated_at else None),
                previewText=preview,
            )
        )
    return items


@app.get("/api/generated-emails/{email_id}", response_model=GeneratedEmailDetail)
def api_generated_email_detail(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GeneratedEmail, email_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generated email not found")
    tags = []
    try:
        tags = json.loads(row.tags_json or "[]")
    except Exception:
        tags = []
    payload = {}
    try:
        payload = json.loads(row.payload_json or "{}")
    except Exception:
        payload = {}
    return GeneratedEmailDetail(
        id=row.id,
        title=row.title or "",
        subject=row.subject or "",
        templateId=row.template_id or "",
        isFavorite=bool(row.is_favorite),
        tags=tags if isinstance(tags, list) else [],
        payload=payload if isinstance(payload, dict) else {},
        htmlSnapshot=row.html_snapshot or "",
        createdAt=(row.created_at.isoformat() if row.created_at else None),
        updatedAt=(row.updated_at.isoformat() if row.updated_at else None),
    )


@app.patch("/api/generated-emails/{email_id}", response_model=GeneratedEmailDetail)
def api_generated_email_update(
    email_id: int,
    payload: GeneratedEmailUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(GeneratedEmail, email_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generated email not found")
    if payload.title is not None:
        row.title = payload.title
    if payload.tags is not None:
        row.tags_json = json.dumps(payload.tags, ensure_ascii=False)
    if payload.isFavorite is not None:
        row.is_favorite = payload.isFavorite
    if payload.subject is not None:
        row.subject = payload.subject
    if payload.templateId is not None:
        row.template_id = payload.templateId
    if payload.payload is not None:
        row.payload_json = json.dumps(payload.payload, ensure_ascii=False)
    if payload.htmlSnapshot is not None:
        row.html_snapshot = payload.htmlSnapshot
    db.commit()
    return api_generated_email_detail(email_id, user, db)


@app.put("/api/generated-emails/{email_id}", response_model=GeneratedEmailDetail)
def api_generated_email_replace(
    email_id: int,
    payload: GeneratedEmailUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Same behavior as PATCH (some clients or proxies block PATCH reliably)."""
    return api_generated_email_update(email_id, payload, user, db)


@app.post("/api/generated-emails", response_model=GeneratedEmailDetail)
def api_generated_email_create(
    payload: GeneratedEmailCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = (payload.title or "").strip() or (payload.subject or "").strip() or "Email copy"
    row = GeneratedEmail(
        user_id=user.id,
        title=title,
        subject=(payload.subject or "").strip(),
        template_id=(payload.templateId or "").strip(),
        payload_json=json.dumps(payload.payload or {}, ensure_ascii=False),
        html_snapshot=payload.htmlSnapshot or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return api_generated_email_detail(row.id, user, db)


@app.delete("/api/generated-emails/{email_id}")
def api_generated_email_delete(email_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(GeneratedEmail, email_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generated email not found")
    db.delete(row)
    db.commit()
    return {"ok": True}

@app.post("/api/export")
def api_export(
    req: ExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the final email HTML using the selected template and user choices.
    """
    # Get the generation session
    session = db.get(GenerationSession, req.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        generation_data = json.loads(session.generation_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid generation data")
    
    # Get company profile
    prof = db.get(CompanyProfile, user.id)
    company_profile = {}
    if prof and prof.data_json:
        try:
            company_profile = json.loads(prof.data_json)
        except Exception:
            company_profile = {}
    
    # Extract selected options
    template_id = generation_data.get("templateId", "t1")
    block_layout = req.blockLayout or generation_data.get("blockLayout")
    if block_layout:
        try:
            block_layout = validate_block_layout(block_layout)
        except TemplateValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    image_options = generation_data.get("imageOptions", [])
    text_options = generation_data.get("textOptions", [])
    cta_options = generation_data.get("ctaOptions", [])
    
    # Get selected items
    selected_image = image_options[req.image_index] if req.image_index < len(image_options) else {}
    selected_text = text_options[req.text_index] if req.text_index < len(text_options) else {}
    selected_cta = cta_options[req.cta_index] if req.cta_index < len(cta_options) else {}

    reqs = _template_generation_requirements(template_id, block_layout, db, user.id)
    if reqs.get("body_count", 1) > 1 and text_options:
        parts = []
        base = max(0, int(req.text_index or 0))
        for i in range(int(reqs.get("body_count", 1))):
            idx = (base + i) % len(text_options)
            txt = (text_options[idx] or {}).get("html", "")
            if txt:
                parts.append(txt)
        selected_text = {"html": "\n<hr/>\n".join(parts)}
    
    template_cfg = _template_config_for_render(template_id, block_layout)
    subject = generation_data.get("subject", "Email")
    body_html = selected_text.get("html", "")
    image_url = selected_image.get("url")
    image_alt = selected_image.get("alt", "Email image")
    cta_link = selected_cta.get("href")
    cta_label = selected_cta.get("label")
    color_scheme = generation_data.get("colorScheme")
    language = generation_data.get("language", "ru")

    if _is_modular_template(template_id) or generation_data.get("isModular"):
        layout = _resolve_block_layout(template_id, block_layout)
        html = render_modular_email(
            layout,
            company_profile=company_profile,
            subject=subject,
            body_html=body_html,
            image_url=image_url,
            image_alt=image_alt,
            cta_link=cta_link,
            cta_label=cta_label,
            theme=template_cfg.get("theme"),
            color_scheme=color_scheme,
            language=language,
            block_content=generation_data.get("blockContent") or {},
        )
    else:
        html = render_template(
            template_id=template_id,
            company_profile=company_profile,
            subject=subject,
            body_html=body_html,
            image_url=image_url,
            image_alt=image_alt,
            cta_link=cta_link,
            cta_label=cta_label,
            color_scheme=color_scheme,
            language=language,
            template_config=template_cfg,
        )
    
    return {"html": html}

# ----------------------------
# Contacts & campaigns (provider: UniSender / SendGrid via email_dispatch)
# ----------------------------

@app.get("/api/contacts/lists")
def api_contacts_lists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"lists": email_dispatch.get_lists(db=db, user_id=user.id)}


@app.post("/api/contacts/lists")
def api_contacts_create_list(
    payload: ContactListCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return email_dispatch.create_list(payload.name, db=db, user_id=user.id)


@app.delete("/api/contacts/lists/{list_id}")
def api_contacts_delete_list(
    list_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not email_dispatch.delete_list(list_id, db=db, user_id=user.id):
        raise HTTPException(status_code=404, detail="List not found")
    return {"ok": True}


@app.get("/api/contacts/lists/{list_id}/contacts")
def api_contacts_list_contacts(
    list_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"contacts": email_dispatch.get_contacts(list_id, db=db, user_id=user.id)}


@app.post("/api/contacts/upload", response_model=list[ContactsUploadResultItem])
def api_contacts_upload(
    payload: ContactsUploadRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = []
    for entry in payload.lists:
        contacts = [c.model_dump() for c in entry.contacts]
        res = email_dispatch.import_contacts(entry.list_id, contacts, db=db, user_id=user.id)
        results.append(ContactsUploadResultItem(
            list_id=entry.list_id,
            list_name=entry.list_name,
            total_contacts=len(entry.contacts),
            uploaded_contacts=int(res.get("uploaded", 0)),
            batches=int(res.get("batches", 0)),
            errors=res.get("errors", []),
        ))
    return results


@app.post("/api/contacts/send-campaign", response_model=ContactsSendCampaignResult)
def api_contacts_send_campaign(
    payload: ContactsSendCampaignRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_row = db.get(GeneratedEmail, payload.generated_email_id)
    if not email_row or email_row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Generated email not found")

    # Resolve campaign HTML: prefer the saved snapshot, else render from the stored
    # payload (parity with /api/send/generated). Persist it so the background sender
    # — which reads generated_email.html_snapshot — has the rendered HTML.
    html = email_row.html_snapshot or ""
    if not html:
        try:
            payload_data = json.loads(email_row.payload_json or "{}")
            sid = str(payload_data.get("sessionId") or "").strip()
            if sid:
                exp = api_export(ExportRequest(session_id=sid, image_index=0, text_index=0, cta_index=0), user, db)
                html = str((exp or {}).get("html") or "")
        except Exception:
            html = ""
    if not html:
        raise HTTPException(status_code=400, detail="No rendered email HTML available — open the email and save it first")
    if email_row.html_snapshot != html:
        email_row.html_snapshot = html
        db.commit()

    subject = payload.subject or email_row.subject or email_row.title or "Email Campaign"

    company_row = db.get(CompanyProfile, user.id)
    company_data: dict = {}
    if company_row:
        try:
            company_data = json.loads(company_row.data_json or "{}")
        except Exception:
            pass
    sys_email, sys_name = email_dispatch.system_sender()
    from_email = company_data.get("senderEmail") or sys_email or ""
    from_name = company_data.get("senderName") or company_data.get("companyName") or sys_name or from_email
    if not from_email:
        raise HTTPException(status_code=400, detail="Sender email not configured (set in Company Profile)")

    result = email_dispatch.send_campaign(
        list_id=payload.list_id,
        subject=subject,
        from_email=from_email,
        from_name=from_name,
        html=html,
        db=db,
        user_id=user.id,
        generated_email_id=email_row.id,
    )
    run_id = result.pop("_run", None)
    if run_id is not None:
        from app import campaign_sender
        background.add_task(campaign_sender.run_campaign, run_id)
    return ContactsSendCampaignResult(
        single_send_id=str(result.get("id", "")),
        status=str(result.get("status", "scheduled")),
        name=str(result.get("name", subject)),
    )


@app.get("/api/analytics/campaigns", response_model=CampaignStatsResponse)
def api_analytics_campaigns(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CampaignStatsResponse(campaigns=email_dispatch.campaign_stats(db=db, user_id=user.id))


@app.post("/api/webhooks/sendgrid/events")
async def api_sendgrid_events(request: Request, db: Session = Depends(get_db)):
    from app import sendgrid_events
    from app.config import SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY
    body = await request.body()
    if SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY:
        sig = request.headers.get("X-Twilio-Email-Event-Webhook-Signature", "")
        ts = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp", "")
        if not sendgrid_events.verify_signature(SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY, body, sig, ts):
            raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        events = json.loads(body or b"[]")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")
    n = sendgrid_events.store_events(db, events if isinstance(events, list) else [])
    return {"stored": n}


# ----------------------------
# Serve static frontend
# ----------------------------
frontend_path = (Path(__file__).resolve().parent / FRONTEND_DIR).resolve()
if not frontend_path.exists():
    # Also try relative to backend working dir
    frontend_path = Path(FRONTEND_DIR).resolve()

app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
