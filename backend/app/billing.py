"""
Server-side token economy: balance, ledger, generation charges, PayPal fulfillment.
Never trust client-reported balances; all mutations go through this module with row locks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import Session

from datetime import datetime, timedelta, timezone

from app.config import (
    TOKENS_PER_TEXT,
    TOKENS_PER_IMAGE,
    TOKEN_USD_REFERENCE,
    FREE_PLAN_GENERATIONS_PER_DAY,
    TOKEN_PLANS,
    PAYPAL_PLAN_ID,
    REPUTATION_DEFAULT,
    REPUTATION_PENALTY_CONTENT_POLICY,
    REPUTATION_ORANGE_THRESHOLD,
    REPUTATION_RECOVERY_AMOUNT,
    REPUTATION_RECOVERY_HOURS,
    REPUTATION_BILLING_PERIOD_DAYS,
    DISABLE_GENERATION_LIMITS,
)
from app.db import engine
from app.models import (
    GenerationLog,
    PaymentFulfillment,
    TokenLedger,
    TokenRefundRequest,
    UserProfile,
)
from app.schemas import Entitlements, TokenPlanPublic

FAILURE_SERVER = "server_error"
FAILURE_CONTENT_POLICY = "content_policy"
REFUND_STATUS_NONE = "none"
REFUND_STATUS_AUTO = "auto_refunded"
REFUND_STATUS_PENDING = "pending"
REFUND_STATUS_APPROVED = "approved"
REFUND_STATUS_DENIED = "denied"

# Profile settings keys users must not set via PATCH /api/account
PROTECTED_PROFILE_SETTINGS_KEYS = frozenset(
    {
        "subscriptionActive",
        "tokenBalance",
        "demoAdmin",
        "paypalSubscriptionId",
        "paypalPlanId",
        "activePlanId",
        "reputationScore",
        "billingPeriodEndsAt",
        "reputationLastRecoveryAt",
    }
)

REPUTATION_ZONE_GOOD = "good"
REPUTATION_ZONE_ORANGE = "orange"
REPUTATION_ZONE_BLOCKED = "blocked"


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        s = str(raw).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _settings_from_profile(profile: UserProfile | None) -> dict[str, Any]:
    if not profile or not profile.settings_json:
        return {}
    try:
        data = json.loads(profile.settings_json)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings_on_profile(profile: UserProfile, settings: dict[str, Any]) -> None:
    profile.settings_json = json.dumps(settings or {}, ensure_ascii=False)


def reputation_zone(score: int) -> str:
    if score <= 0:
        return REPUTATION_ZONE_BLOCKED
    if score < REPUTATION_ORANGE_THRESHOLD:
        return REPUTATION_ZONE_ORANGE
    return REPUTATION_ZONE_GOOD


def reputation_allows_generation(score: int) -> bool:
    return score > 0


def reputation_allows_images(score: int) -> bool:
    return score >= REPUTATION_ORANGE_THRESHOLD


def reputation_allows_refunds(score: int) -> bool:
    return score >= REPUTATION_ORANGE_THRESHOLD


def extend_billing_period(settings: dict[str, Any], *, days: int | None = None) -> dict[str, Any]:
    out = dict(settings)
    period_days = days if days is not None else REPUTATION_BILLING_PERIOD_DAYS
    now = datetime.now(timezone.utc)
    current_end = _parse_iso_datetime(out.get("billingPeriodEndsAt"))
    base = current_end if current_end and current_end > now else now
    out["billingPeriodEndsAt"] = (base + timedelta(days=period_days)).isoformat()
    return out


def get_reputation_score(db: Session, user_id: int) -> int:
    profile = db.get(UserProfile, user_id)
    if not profile:
        return REPUTATION_DEFAULT
    return max(0, min(100, int(profile.reputation_score or REPUTATION_DEFAULT)))


def apply_reputation_recovery(db: Session, user_id: int) -> int:
    """+10 per 24h while score is 1–99. At 0, no passive recovery."""
    profile = _lock_profile(db, user_id)
    score = max(0, min(100, int(profile.reputation_score or REPUTATION_DEFAULT)))
    if score <= 0 or score >= REPUTATION_DEFAULT:
        return score
    now = datetime.now(timezone.utc)
    last = profile.reputation_last_recovery_at
    if last is not None:
        if hasattr(last, "tzinfo") and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elif not hasattr(last, "tzinfo"):
            last = _parse_iso_datetime(str(last))
    if last is None:
        profile.reputation_last_recovery_at = now
        db.flush()
        return score
    elapsed_h = (now - last).total_seconds() / 3600.0
    intervals = int(elapsed_h // REPUTATION_RECOVERY_HOURS)
    if intervals <= 0:
        return score
    gain = intervals * REPUTATION_RECOVERY_AMOUNT
    score = min(REPUTATION_DEFAULT, score + gain)
    profile.reputation_score = score
    profile.reputation_last_recovery_at = now
    db.flush()
    return score


def maybe_restore_reputation_on_billing_period(
    db: Session,
    user_id: int,
    settings: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """At reputation 0, restore to 100 when the billing period rolls over (subscribers)."""
    profile = _lock_profile(db, user_id)
    score = max(0, min(100, int(profile.reputation_score or 0)))
    if score != 0:
        return settings, score
    if not has_active_subscription(settings):
        return settings, 0
    end = _parse_iso_datetime(settings.get("billingPeriodEndsAt"))
    if not end or datetime.now(timezone.utc) < end:
        return settings, 0
    profile.reputation_score = REPUTATION_DEFAULT
    profile.reputation_last_recovery_at = datetime.now(timezone.utc)
    settings = extend_billing_period(settings)
    _write_settings_on_profile(profile, settings)
    db.flush()
    return settings, REPUTATION_DEFAULT


def sync_user_reputation(
    db: Session,
    user_id: int,
    settings: dict[str, Any] | None,
) -> tuple[int, dict[str, Any]]:
    settings = dict(settings or {})
    settings, score = maybe_restore_reputation_on_billing_period(db, user_id, settings)
    if score == 0:
        return 0, settings
    score = apply_reputation_recovery(db, user_id)
    return score, settings


def reputation_blocked_until(settings: dict[str, Any], score: int) -> str | None:
    if score > 0:
        return None
    raw = settings.get("billingPeriodEndsAt")
    return str(raw).strip() if raw else None


def reputation_blocked_message(lang: str, settings: dict[str, Any]) -> str:
    lang = (lang or "").lower()
    until = reputation_blocked_until(settings, 0)
    if lang.startswith("e"):
        if until:
            return (
                "Generation is disabled because your reputation is 0. "
                f"Access restores at the start of your next billing period ({until[:10]}). "
                "Refunds are not issued while reputation is below 40."
            )
        return (
            "Generation is disabled because your reputation is 0. "
            "Subscribe or wait for your next billing period. Refunds are not issued below 40 reputation."
        )
    if until:
        return (
            "Генерация недоступна: репутация 0. "
            f"Доступ восстановится в начале следующего биллинг-периода ({until[:10]}). "
            "Возвраты не выполняются при репутации ниже 40."
        )
    return (
        "Генерация недоступна: репутация 0. "
        "Оформите подписку или дождитесь нового биллинг-периода. "
        "Возвраты не выполняются при репутации ниже 40."
    )


def restore_reputation_on_payment(db: Session, user_id: int) -> None:
    profile = _lock_profile(db, user_id)
    profile.reputation_score = REPUTATION_DEFAULT
    profile.reputation_last_recovery_at = datetime.now(timezone.utc)
    settings = _settings_from_profile(profile)
    settings = extend_billing_period(settings)
    _write_settings_on_profile(profile, settings)
    db.flush()


def apply_content_policy_violation(db: Session, user_id: int) -> int:
    profile = _lock_profile(db, user_id)
    current = max(0, min(100, int(profile.reputation_score or REPUTATION_DEFAULT)))
    profile.reputation_score = max(0, current - REPUTATION_PENALTY_CONTENT_POLICY)
    db.flush()
    return int(profile.reputation_score)


def content_policy_failure_message(lang: str, reputation: int) -> str:
    lang = (lang or "").lower()
    if lang.startswith("e"):
        return (
            "Your request violates our content policy. Tokens are not refunded for disallowed "
            f"content. Account reputation: {reputation}/100. Repeated violations may limit access."
        )
    return (
        "Запрос нарушает правила контента. Токены за такие генерации не возвращаются. "
        f"Репутация аккаунта: {reputation}/100. Повторные нарушения могут ограничить доступ."
    )


def tokens_were_refunded(db: Session, billing_ref: str) -> bool:
    ref = (billing_ref or "").strip()
    if not ref:
        return False
    return (
        db.scalar(select(TokenLedger).where(TokenLedger.ref_id == f"refund:{ref}")) is not None
    )


def mark_billing_refunded(billing: dict[str, Any]) -> dict[str, Any]:
    out = dict(billing)
    out["refunded"] = True
    return out


def handle_generation_failure(
    db: Session,
    *,
    user_id: int,
    billing: dict[str, Any],
    failure_kind: str,
    lang: str = "en",
) -> str:
    """
    Apply refund policy: server errors auto-refund; content-policy violations do not.
    Returns extra user-facing message (empty for server errors after refund).
    """
    kind = (failure_kind or FAILURE_SERVER).strip()
    if kind == FAILURE_CONTENT_POLICY:
        reputation = apply_content_policy_violation(db, user_id)
        return content_policy_failure_message(lang, reputation)
    if not reputation_allows_refunds(get_reputation_score(db, user_id)):
        return ""
    refund_generation_charge(db, user_id=user_id, billing=billing)
    return ""


def job_refund_status(db: Session, user_id: int, job_id: str, billing: dict[str, Any]) -> str:
    ref = (billing.get("ref") or "").strip()
    charged = int(billing.get("tokensCharged") or 0)
    mode = (billing.get("mode") or "").strip()
    if mode != "tokens" or charged <= 0:
        return REFUND_STATUS_NONE
    if billing.get("refunded") or tokens_were_refunded(db, ref):
        return REFUND_STATUS_AUTO
    req = db.scalar(
        select(TokenRefundRequest)
        .where(
            TokenRefundRequest.user_id == user_id,
            TokenRefundRequest.job_id == job_id,
        )
        .order_by(TokenRefundRequest.id.desc())
    )
    if not req:
        return REFUND_STATUS_NONE
    if req.status == "approved":
        return REFUND_STATUS_APPROVED
    if req.status == "denied":
        return REFUND_STATUS_DENIED
    return REFUND_STATUS_PENDING


def can_request_refund(
    db: Session,
    user_id: int,
    job_id: str,
    billing: dict[str, Any],
    failure_kind: str,
) -> bool:
    ref = (billing.get("ref") or "").strip()
    charged = int(billing.get("tokensCharged") or 0)
    if (billing.get("mode") or "") != "tokens" or charged <= 0:
        return False
    if tokens_were_refunded(db, ref):
        return False
    if not reputation_allows_refunds(get_reputation_score(db, user_id)):
        return False
    existing = db.scalar(
        select(TokenRefundRequest).where(
            TokenRefundRequest.user_id == user_id,
            TokenRefundRequest.job_id == job_id,
            TokenRefundRequest.status == "pending",
        )
    )
    if existing:
        return False
    # Manual review for server errors (auto-refund may have failed) or disputed cases
    return True


def create_refund_request(
    db: Session,
    *,
    user_id: int,
    job_id: str,
    billing: dict[str, Any],
    failure_kind: str,
    user_message: str,
) -> TokenRefundRequest:
    ref = (billing.get("ref") or "").strip()
    charged = int(billing.get("tokensCharged") or 0)
    if not can_request_refund(db, user_id, job_id, billing, failure_kind):
        raise HTTPException(
            status_code=409,
            detail="Refund cannot be requested for this generation",
        )
    row = TokenRefundRequest(
        user_id=user_id,
        job_id=job_id[:40],
        billing_ref=ref[:128],
        tokens_requested=charged,
        failure_kind=(failure_kind or "")[:32],
        user_message=(user_message or "").strip()[:2000],
        status="pending",
    )
    db.add(row)
    db.flush()
    return row


def resolve_refund_request(
    db: Session,
    *,
    request_id: int,
    approve: bool,
    admin_note: str = "",
) -> TokenRefundRequest:
    row = db.get(TokenRefundRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="Request already resolved")
    row.admin_note = (admin_note or "").strip()[:2000]
    row.resolved_at = datetime.now(timezone.utc)
    if approve:
        if not reputation_allows_refunds(get_reputation_score(db, row.user_id)):
            raise HTTPException(
                status_code=409,
                detail="Refunds are not issued when reputation is below 40",
            )
        refund_tokens_idempotent(
            db,
            user_id=row.user_id,
            amount=row.tokens_requested,
            original_ref_id=row.billing_ref,
        )
        row.status = "approved"
    else:
        row.status = "denied"
    db.flush()
    return row


@dataclass(frozen=True)
class GenerationBillingResult:
    mode: str  # "tokens" | "free"
    tokens_charged: int
    text_tokens_charged: int
    image_tokens_charged: int
    variant_count: int
    image_slots: int
    cta_slots: int
    refine_allowed: bool
    images_allowed: bool = True


@dataclass(frozen=True)
class GenerationCostQuote:
    text_tokens: int
    image_tokens: int
    total_tokens: int
    include_image: bool


def generation_token_cost(*, include_image: bool) -> GenerationCostQuote:
    text = TOKENS_PER_TEXT
    image = TOKENS_PER_IMAGE if include_image else 0
    return GenerationCostQuote(
        text_tokens=text,
        image_tokens=image,
        total_tokens=text + image,
        include_image=include_image,
    )


def refine_token_cost(*, refine_text: bool, refine_image: bool) -> GenerationCostQuote:
    text = TOKENS_PER_TEXT if refine_text else 0
    image = TOKENS_PER_IMAGE if refine_image else 0
    if text == 0 and image == 0:
        text = TOKENS_PER_TEXT
    return GenerationCostQuote(
        text_tokens=text,
        image_tokens=image,
        total_tokens=text + image,
        include_image=refine_image,
    )


def plan_by_id(plan_id: str) -> dict[str, Any] | None:
    pid = (plan_id or "").strip()
    if not pid:
        return None
    for plan in TOKEN_PLANS:
        if str(plan.get("id") or "").strip() == pid:
            return plan
    return None


def plan_is_free(plan: dict[str, Any] | None) -> bool:
    return bool(plan and plan.get("isFree"))


def paid_plans_raw() -> list[dict[str, Any]]:
    return [p for p in TOKEN_PLANS if not p.get("isFree")]


def free_plan_raw() -> dict[str, Any] | None:
    for p in TOKEN_PLANS:
        if p.get("isFree"):
            return p
    return None


def has_active_subscription(settings: dict[str, Any]) -> bool:
    active = (settings.get("activePlanId") or "").strip()
    if not active:
        return False
    plan = plan_by_id(active)
    return bool(plan) and not plan_is_free(plan)


def topup_price_usd(token_count: int, plan: dict[str, Any]) -> float:
    rate = float(plan.get("extraTokenUsdPerToken") or TOKEN_USD_REFERENCE)
    return round(max(0, int(token_count)) * rate, 2)


def _plan_by_paypal_id(paypal_plan_id: str) -> dict[str, Any] | None:
    pid = (paypal_plan_id or "").strip()
    if not pid:
        return None
    for plan in TOKEN_PLANS:
        if (plan.get("paypalPlanId") or "").strip() == pid:
            return plan
    paid = paid_plans_raw()
    if PAYPAL_PLAN_ID and PAYPAL_PLAN_ID.strip() == pid and paid:
        return paid[0]
    return None


def _plan_to_public(p: dict[str, Any]) -> TokenPlanPublic:
    is_free = bool(p.get("isFree"))
    cents = int(p.get("priceUsdCents") or 0)
    extra_rate = float(p.get("extraTokenUsdPerToken") or TOKEN_USD_REFERENCE)
    return TokenPlanPublic(
        id=str(p.get("id") or ""),
        name=str(p.get("name") or "Plan"),
        tokens=int(p.get("tokens") or 0),
        priceUsdCents=cents,
        displayPrice="Free" if is_free else f"${cents / 100:.2f}",
        cycleLabel=str(p.get("cycleLabel") or "month"),
        paypalPlanId=("" if is_free else (p.get("paypalPlanId") or PAYPAL_PLAN_ID or "")).strip(),
        description=str(p.get("description") or ""),
        extraTokenUsdPerToken=extra_rate,
        extraTokenDisplayPrice=f"${extra_rate:.3f}",
        isFree=is_free,
        freeGenerationsPerDay=int(p.get("freeGenerationsPerDay") or 0) if is_free else 0,
    )


def public_plans(*, paid_only: bool = False) -> list[TokenPlanPublic]:
    source = paid_plans_raw() if paid_only else TOKEN_PLANS
    return [_plan_to_public(p) for p in source]


def public_free_plan() -> TokenPlanPublic | None:
    raw = free_plan_raw()
    return _plan_to_public(raw) if raw else None


def _lock_profile(db: Session, user_id: int) -> UserProfile:
    row = db.scalar(
        select(UserProfile).where(UserProfile.user_id == user_id).with_for_update()
    )
    if not row:
        row = UserProfile(
            user_id=user_id,
            token_balance=0,
            reputation_score=REPUTATION_DEFAULT,
        )
        db.add(row)
        db.flush()
    return row


def get_token_balance(db: Session, user_id: int) -> int:
    profile = db.get(UserProfile, user_id)
    if not profile:
        return 0
    return max(0, int(profile.token_balance or 0))


def _generation_uses_today(db: Session, user_id: int) -> int:
    if engine.dialect.name == "sqlite":
        day_cond = func.date(GenerationLog.created_at) == func.date("now")
    else:
        day_cond = cast(GenerationLog.created_at, Date) == func.current_date()
    n = db.scalar(
        select(func.count()).select_from(GenerationLog).where(
            GenerationLog.user_id == user_id, day_cond
        )
    )
    return int(n or 0)


def entitlements_for_user(
    db: Session,
    user_id: int,
    *,
    settings: dict[str, Any] | None = None,
) -> Entitlements:
    balance = get_token_balance(db, user_id)
    used = _generation_uses_today(db, user_id)
    free_limit = FREE_PLAN_GENERATIONS_PER_DAY
    free_remaining = max(0, free_limit - used)
    full_gen_cost = generation_token_cost(include_image=True).total_tokens
    min_gen_cost = TOKENS_PER_TEXT
    can_tokens = balance >= min_gen_cost
    can_free = free_remaining > 0
    paid_path = balance >= full_gen_cost or can_tokens
    rep_settings = dict(settings or {})
    reputation, rep_settings = sync_user_reputation(db, user_id, rep_settings)
    zone = reputation_zone(reputation)
    can_gen = reputation_allows_generation(reputation)
    can_images = reputation_allows_images(reputation)
    refunds_ok = reputation_allows_refunds(reputation)
    active_plan_id = ""
    has_sub = False
    can_topup = False
    if settings is not None:
        active_plan_id = str(rep_settings.get("activePlanId") or "").strip()
        has_sub = has_active_subscription(rep_settings)
        can_topup = has_sub
    if not can_gen:
        can_tokens = False
        can_free = False
    if DISABLE_GENERATION_LIMITS:
        # Unlimited generation: never gate the UI on balance, free quota or reputation.
        can_tokens = True
        can_free = True
        can_gen = True
        can_images = True
        refunds_ok = True
        paid_path = True
    return Entitlements(
        tokenBalance=balance,
        tokensPerText=TOKENS_PER_TEXT,
        tokensPerImage=TOKENS_PER_IMAGE,
        tokensPerGeneration=full_gen_cost,
        tokensPerRefine=TOKENS_PER_TEXT + TOKENS_PER_IMAGE,
        tokenUsdReference=TOKEN_USD_REFERENCE,
        generationsUsedToday=used,
        freeGenerationsPerDay=free_limit,
        freeGenerationsRemainingToday=free_remaining,
        canGenerateWithTokens=can_tokens,
        canGenerateFreeToday=can_free,
        refineAllowed=balance >= TOKENS_PER_TEXT,
        imageOptionsCount=3 if paid_path else 1,
        ctaOptionsCount=3 if paid_path else 2,
        hasActiveSubscription=has_sub,
        canTopUpTokens=can_topup,
        activePlanId=active_plan_id,
        subscriptionActive=has_sub,
        generationsLimitPerDay=free_limit if not can_tokens else None,
        reputationScore=reputation,
        reputationZone=zone,
        canGenerate=can_gen,
        canGenerateImages=can_images,
        refundsAllowed=refunds_ok,
        reputationBlockedUntil=reputation_blocked_until(rep_settings, reputation),
    )


def _ledger_entry(
    db: Session,
    *,
    user_id: int,
    delta: int,
    balance_after: int,
    reason: str,
    ref_id: str,
) -> None:
    db.add(
        TokenLedger(
            user_id=user_id,
            delta=delta,
            balance_after=balance_after,
            reason=reason[:64],
            ref_id=ref_id[:128],
        )
    )


def credit_tokens_idempotent(
    db: Session,
    *,
    user_id: int,
    tokens: int,
    external_id: str,
    reason: str,
    plan_id: str = "",
    amount_cents: int | None = None,
) -> bool:
    """
    Credit tokens once per external_id (PayPal sale id, etc.).
    Returns True if credited, False if already processed.
    """
    if tokens <= 0:
        return False
    ext = (external_id or "").strip()
    if not ext:
        raise ValueError("external_id is required for idempotent credit")
    existing = db.scalar(
        select(PaymentFulfillment).where(PaymentFulfillment.external_id == ext)
    )
    if existing:
        return False

    profile = _lock_profile(db, user_id)
    new_balance = max(0, int(profile.token_balance or 0)) + int(tokens)
    profile.token_balance = new_balance
    _ledger_entry(
        db,
        user_id=user_id,
        delta=int(tokens),
        balance_after=new_balance,
        reason=reason,
        ref_id=ext,
    )
    db.add(
        PaymentFulfillment(
            external_id=ext,
            user_id=user_id,
            plan_id=(plan_id or "")[:64],
            tokens_granted=int(tokens),
            amount_cents=amount_cents,
            provider="paypal",
        )
    )
    db.flush()
    return True


def debit_tokens(
    db: Session,
    *,
    user_id: int,
    amount: int,
    reason: str,
    ref_id: str,
) -> int:
    """Debit tokens if balance sufficient. Returns new balance. Raises HTTPException if not."""
    if amount <= 0:
        return get_token_balance(db, user_id)
    ref = (ref_id or "").strip()
    if not ref:
        raise ValueError("ref_id is required for debits")

    dup = db.scalar(select(TokenLedger).where(TokenLedger.ref_id == ref))
    if dup:
        return int(dup.balance_after or 0)

    profile = _lock_profile(db, user_id)
    balance = max(0, int(profile.token_balance or 0))
    if balance < amount:
        raise HTTPException(status_code=403, detail="Insufficient token balance")
    new_balance = balance - amount
    profile.token_balance = new_balance
    _ledger_entry(
        db,
        user_id=user_id,
        delta=-amount,
        balance_after=new_balance,
        reason=reason,
        ref_id=ref,
    )
    db.flush()
    return new_balance


def refund_tokens_idempotent(
    db: Session,
    *,
    user_id: int,
    amount: int,
    original_ref_id: str,
) -> bool:
    """Refund a prior debit (e.g. failed generation). Idempotent per original_ref_id."""
    if amount <= 0:
        return False
    refund_ref = f"refund:{original_ref_id}"
    if db.scalar(select(TokenLedger).where(TokenLedger.ref_id == refund_ref)):
        return False
    orig = db.scalar(
        select(TokenLedger).where(
            TokenLedger.user_id == user_id,
            TokenLedger.ref_id == original_ref_id,
            TokenLedger.delta < 0,
        )
    )
    if not orig:
        return False

    profile = _lock_profile(db, user_id)
    new_balance = max(0, int(profile.token_balance or 0)) + amount
    profile.token_balance = new_balance
    _ledger_entry(
        db,
        user_id=user_id,
        delta=amount,
        balance_after=new_balance,
        reason="refund",
        ref_id=refund_ref,
    )
    db.flush()
    return True


def _quota_message(lang: str, ent: Entitlements, needed: int) -> str:
    lang = (lang or "").lower()
    if lang.startswith("e"):
        if ent.canGenerateWithTokens or ent.tokenBalance > 0:
            return (
                f"Insufficient tokens ({ent.tokenBalance} available, "
                f"{needed} required for this generation)."
            )
        return (
            f"Daily free generation limit reached ({ent.freeGenerationsPerDay} per day). "
            "Upgrade your plan or buy tokens to continue."
        )
    if ent.canGenerateWithTokens or ent.tokenBalance > 0:
        return (
            f"Недостаточно токенов (доступно {ent.tokenBalance}, "
            f"нужно {needed} за эту генерацию)."
        )
    return (
        f"Достигнут дневной лимит бесплатных генераций ({ent.freeGenerationsPerDay} в день). "
        "Оформите подписку или купите токены."
    )


def charge_for_generation(
    db: Session,
    *,
    user_id: int,
    ref_id: str,
    lang: str = "en",
    include_image: bool = True,
) -> GenerationBillingResult:
    """
    Reserve billing for one generation: deduct tokens or consume today's free slot.
    Idempotent per ref_id (same job retried with same ref won't double-charge).
    """
    ref = (ref_id or "").strip()
    if not ref:
        raise ValueError("ref_id is required")

    existing = db.scalar(
        select(TokenLedger).where(
            TokenLedger.user_id == user_id,
            TokenLedger.ref_id == ref,
        )
    )
    settings: dict[str, Any] = {}
    profile_for_settings = db.get(UserProfile, user_id)
    if profile_for_settings:
        settings = _settings_from_profile(profile_for_settings)
    reputation, settings = sync_user_reputation(db, user_id, settings)

    if DISABLE_GENERATION_LIMITS:
        # No tokens, no daily quota, no reputation gating — generation always works fully.
        return GenerationBillingResult(
            mode="tokens",
            tokens_charged=0,
            text_tokens_charged=0,
            image_tokens_charged=0,
            variant_count=3,
            image_slots=3,
            cta_slots=3,
            refine_allowed=True,
            images_allowed=include_image,
        )

    if not reputation_allows_generation(reputation):
        raise HTTPException(
            status_code=403,
            detail=reputation_blocked_message(lang, settings),
        )
    effective_image = include_image and reputation_allows_images(reputation)
    cost = generation_token_cost(include_image=effective_image)

    if existing:
        ent = entitlements_for_user(db, user_id, settings=settings)
        mode = "tokens" if existing.delta < 0 else "free"
        paid = mode == "tokens"
        charged = abs(existing.delta) if existing.delta < 0 else 0
        return GenerationBillingResult(
            mode=mode,
            tokens_charged=charged,
            text_tokens_charged=TOKENS_PER_TEXT if charged else 0,
            image_tokens_charged=max(0, charged - TOKENS_PER_TEXT),
            variant_count=3 if paid else 2,
            image_slots=3 if paid else 1,
            cta_slots=3 if paid else 2,
            refine_allowed=ent.refineAllowed,
            images_allowed=reputation_allows_images(reputation),
        )

    ent = entitlements_for_user(db, user_id, settings=settings)

    # Free daily generations are consumed before any token charge.
    if ent.canGenerateFreeToday:
        db.add(GenerationLog(user_id=user_id))
        db.flush()
        _ledger_entry(
            db,
            user_id=user_id,
            delta=0,
            balance_after=get_token_balance(db, user_id),
            reason="free_generation",
            ref_id=ref,
        )
        db.flush()
        return GenerationBillingResult(
            mode="free",
            tokens_charged=0,
            text_tokens_charged=0,
            image_tokens_charged=0,
            variant_count=2,
            image_slots=1,
            cta_slots=2,
            refine_allowed=False,
            images_allowed=effective_image,
        )

    if ent.tokenBalance >= cost.total_tokens:
        debit_tokens(
            db,
            user_id=user_id,
            amount=cost.total_tokens,
            reason="generation",
            ref_id=ref,
        )
        return GenerationBillingResult(
            mode="tokens",
            tokens_charged=cost.total_tokens,
            text_tokens_charged=cost.text_tokens,
            image_tokens_charged=cost.image_tokens,
            variant_count=3,
            image_slots=3,
            cta_slots=3,
            refine_allowed=True,
            images_allowed=effective_image,
        )

    raise HTTPException(status_code=403, detail=_quota_message(lang, ent, cost.total_tokens))


def charge_for_refine(
    db: Session,
    *,
    user_id: int,
    ref_id: str,
    lang: str = "en",
    refine_text: bool = False,
    refine_image: bool = False,
) -> GenerationBillingResult:
    ref = (ref_id or "").strip()
    if not ref:
        raise ValueError("ref_id is required")
    settings: dict[str, Any] = {}
    profile_for_settings = db.get(UserProfile, user_id)
    if profile_for_settings:
        settings = _settings_from_profile(profile_for_settings)
    reputation, settings = sync_user_reputation(db, user_id, settings)
    if not reputation_allows_generation(reputation):
        raise HTTPException(
            status_code=403,
            detail=reputation_blocked_message(lang, settings),
        )
    if refine_image and not reputation_allows_images(reputation):
        lang = (lang or "").lower()
        if lang.startswith("e"):
            detail = (
                f"Image refinements require reputation {REPUTATION_ORANGE_THRESHOLD}+ "
                f"(yours: {reputation}). Text-only edits are still available."
            )
        else:
            detail = (
                f"Правка изображений доступна при репутации {REPUTATION_ORANGE_THRESHOLD}+ "
                f"(у вас: {reputation}). Доступна правка только текста."
            )
        raise HTTPException(status_code=403, detail=detail)
    cost = refine_token_cost(refine_text=refine_text, refine_image=refine_image)
    ent = entitlements_for_user(db, user_id, settings=settings)
    if ent.tokenBalance < cost.total_tokens:
        lang = (lang or "").lower()
        if lang.startswith("e"):
            detail = (
                f"Refinement requires {cost.total_tokens} tokens "
                f"({ent.tokenBalance} available). Buy tokens to continue."
            )
        else:
            detail = (
                f"Для правки нужно {cost.total_tokens} токенов "
                f"(доступно {ent.tokenBalance}). Купите токены."
            )
        raise HTTPException(status_code=403, detail=detail)
    debit_tokens(
        db,
        user_id=user_id,
        amount=cost.total_tokens,
        reason="refine",
        ref_id=ref,
    )
    return GenerationBillingResult(
        mode="tokens",
        tokens_charged=cost.total_tokens,
        text_tokens_charged=cost.text_tokens,
        image_tokens_charged=cost.image_tokens,
        variant_count=3,
        image_slots=3,
        cta_slots=3,
        refine_allowed=True,
        images_allowed=reputation_allows_images(reputation),
    )


def refund_generation_charge(
    db: Session,
    *,
    user_id: int,
    billing: dict[str, Any],
) -> None:
    mode = (billing.get("mode") or "").strip()
    ref = (billing.get("ref") or "").strip()
    charged = int(billing.get("tokensCharged") or 0)
    if not ref:
        return
    if not reputation_allows_refunds(get_reputation_score(db, user_id)):
        return
    if mode == "tokens" and charged > 0:
        refund_tokens_idempotent(db, user_id=user_id, amount=charged, original_ref_id=ref)
    elif mode == "free":
        # Remove free-slot ledger marker so user can try again same day
        row = db.scalar(
            select(TokenLedger).where(
                TokenLedger.user_id == user_id,
                TokenLedger.ref_id == ref,
                TokenLedger.reason == "free_generation",
            )
        )
        if row:
            db.delete(row)
        log = db.scalar(
            select(GenerationLog)
            .where(GenerationLog.user_id == user_id)
            .order_by(GenerationLog.id.desc())
            .limit(1)
        )
        if log:
            db.delete(log)
    db.flush()


def _parse_amount_cents(resource: dict[str, Any]) -> int | None:
    amount = resource.get("amount") or {}
    if isinstance(amount, dict):
        raw = amount.get("total") or amount.get("value")
        currency = (amount.get("currency") or amount.get("currency_code") or "USD").upper()
    else:
        raw = resource.get("amount")
        currency = "USD"
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if currency != "USD":
        return None
    return int(round(value * 100))


def activate_subscription_plan(
    db: Session,
    *,
    user_id: int,
    plan_id: str,
    paypal_plan_id: str = "",
) -> None:
    plan = plan_by_id(plan_id) or _plan_by_paypal_id(paypal_plan_id)
    if not plan or plan_is_free(plan):
        return
    profile = _lock_profile(db, user_id)
    settings: dict[str, Any] = {}
    if profile.settings_json:
        try:
            settings = json.loads(profile.settings_json)
            if not isinstance(settings, dict):
                settings = {}
        except Exception:
            settings = {}
    settings["activePlanId"] = str(plan.get("id") or "")
    if paypal_plan_id:
        settings["paypalPlanId"] = paypal_plan_id
    profile.settings_json = json.dumps(settings, ensure_ascii=False)
    db.flush()


def fulfill_token_topup(
    db: Session,
    *,
    user_id: int,
    token_count: int,
    external_id: str,
    plan_id: str = "",
    amount_cents: int | None = None,
) -> bool:
    if token_count <= 0:
        return False
    return credit_tokens_idempotent(
        db,
        user_id=user_id,
        tokens=token_count,
        external_id=f"topup:{external_id}",
        reason="token_topup",
        plan_id=plan_id,
        amount_cents=amount_cents,
    )


def parse_topup_custom_id(custom_id: str) -> tuple[int, int, str] | None:
    """
    Parse PayPal custom_id: topup:{user_id}:{token_count}:{plan_id}
    Returns (user_id, token_count, plan_id) or None.
    """
    parts = (custom_id or "").strip().split(":")
    if len(parts) < 4 or parts[0] != "topup":
        return None
    try:
        uid = int(parts[1])
        count = int(parts[2])
        plan_id = ":".join(parts[3:]) if len(parts) > 4 else parts[3]
    except (TypeError, ValueError):
        return None
    if count <= 0 or count > 1_000_000:
        return None
    return uid, count, plan_id


def fulfill_paypal_payment(
    db: Session,
    *,
    user_id: int,
    event_type: str,
    resource: dict[str, Any],
    paypal_plan_id: str = "",
) -> bool:
    """
    Credit tokens from PayPal subscription / sale events.
    Verifies amount matches configured plan when present.
    """
    # Credit only on completed payments (avoids double-credit with SUBSCRIPTION.ACTIVATED).
    et = (event_type or "").strip().upper()
    if et != "PAYMENT.SALE.COMPLETED":
        return False

    plan = _plan_by_paypal_id(paypal_plan_id) or (paid_plans_raw()[0] if paid_plans_raw() else None)
    if not plan or plan_is_free(plan):
        return False

    expected_cents = int(plan.get("priceUsdCents") or 0)
    tokens = int(plan.get("tokens") or 0)
    plan_id = str(plan.get("id") or "")

    amount_cents = _parse_amount_cents(resource)
    if amount_cents is not None and expected_cents > 0 and amount_cents != expected_cents:
        return False

    external_id = (
        str(resource.get("id") or "").strip()
        or str(resource.get("sale_id") or "").strip()
        or f"{et}:{resource.get('billing_agreement_id') or resource.get('id') or ''}"
    )
    if not external_id or external_id == f"{et}:":
        return False

    credited = credit_tokens_idempotent(
        db,
        user_id=user_id,
        tokens=tokens,
        external_id=f"paypal:{external_id}",
        reason="paypal_payment",
        plan_id=plan_id,
        amount_cents=amount_cents if amount_cents is not None else expected_cents,
    )
    if credited:
        activate_subscription_plan(db, user_id=user_id, plan_id=plan_id, paypal_plan_id=paypal_plan_id)
        restore_reputation_on_payment(db, user_id)
    return credited


def billing_json(
    mode: str,
    tokens_charged: int,
    ref: str,
    *,
    text_tokens: int = 0,
    image_tokens: int = 0,
    images_allowed: bool = True,
) -> str:
    return json.dumps(
        {
            "mode": mode,
            "tokensCharged": tokens_charged,
            "textTokens": text_tokens,
            "imageTokens": image_tokens,
            "imagesAllowed": images_allowed,
            "ref": ref,
        },
        ensure_ascii=False,
    )


def parse_billing_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
