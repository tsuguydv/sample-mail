from sqlalchemy import String, DateTime, func, Text, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class GenerationSession(Base):
    __tablename__ = "generation_sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    generation_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_email_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GenerationJob(Base):
    """
    Async email generation job (POST /api/generate/start).
    Progress is polled via GET /api/generate/status/{id}.
    """

    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    step_key: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    request_json: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    failure_kind: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GenerationLog(Base):
    """
    One row per successful POST /api/generate (not deleted when user removes saved emails).
    Used for free-plan daily limits.
    """
    __tablename__ = "generation_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subject: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    template_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    html_snapshot: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    avatar_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    settings_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reputation_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    reputation_last_recovery_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TokenLedger(Base):
    """Append-only audit log for token balance changes."""

    __tablename__ = "token_ledger"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PaymentFulfillment(Base):
    """Idempotent record of external payment events that credited tokens."""

    __tablename__ = "payment_fulfillments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    tokens_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="paypal", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TokenRefundRequest(Base):
    """User-requested token refund review (e.g. disputed server failure)."""

    __tablename__ = "token_refund_requests"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    billing_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    tokens_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_kind: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    user_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    admin_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserTemplate(Base):
    """User-saved email layouts (modular block stacks)."""

    __tablename__ = "user_templates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    base_template_id: Mapped[str] = mapped_column(String(64), nullable=False, default="custom")
    is_modular: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    layout_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    theme_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ContactList(Base):
    """Contact list stored locally (Email-API path, replaces SendGrid Marketing Lists)."""

    __tablename__ = "contact_lists"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("list_id", "email", name="uq_contact_list_email"),)


class EmailCampaign(Base):
    """A bulk send to a contact list via /v3/mail/send (replaces SendGrid Single Send)."""

    __tablename__ = "email_campaigns"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    list_id: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_email_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    from_email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    from_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailEvent(Base):
    """SendGrid Event Webhook record, attributed to a campaign via custom_args."""

    __tablename__ = "email_events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), default="", nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    sg_event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    occurred_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
