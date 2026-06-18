"""Send a campaign to a contact list via SendGrid Email API (/v3/mail/send)."""
from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.config import SENDGRID_API_KEY, SENDGRID_ASM_GROUP_ID
from app.models import Contact, EmailCampaign

_MAIL_SEND_URL = "https://api.sendgrid.com/v3/mail/send"


def build_batches(contacts: list[dict], size: int = 1000) -> list[list[dict]]:
    return [contacts[i:i + size] for i in range(0, len(contacts), size)]


def build_mail_payload(*, batch, campaign_id, user_id, subject, from_email, from_name, html) -> dict:
    personalizations = [{
        "to": [{"email": c["email"]}],
        "custom_args": {"campaign_id": str(campaign_id), "user_id": str(user_id)},
    } for c in batch if c.get("email")]
    payload = {
        "personalizations": personalizations,
        "from": {"email": from_email, "name": from_name or from_email},
        "subject": subject,
        "content": [{"type": "text/html", "value": html or ""}],
        # Category lets us pull per-campaign stats from SendGrid by polling (no webhook /
        # public URL needed) — see sendgrid_stats.fetch_campaign_stats.
        "categories": [f"campaign_{campaign_id}"],
        "tracking_settings": {
            "open_tracking": {"enable": True},
            "click_tracking": {"enable": True, "enable_text": False},
        },
    }
    if SENDGRID_ASM_GROUP_ID:
        payload["asm"] = {"group_id": SENDGRID_ASM_GROUP_ID}
    return payload


def _send_batch(payload: dict) -> None:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            _MAIL_SEND_URL,
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"mail/send {r.status_code}: {r.text[:300]}")


def _campaign_html(db: Session, camp: EmailCampaign) -> str:
    from app.models import GeneratedEmail
    if camp.generated_email_id:
        ge = db.get(GeneratedEmail, camp.generated_email_id)
        if ge and ge.html_snapshot:
            return ge.html_snapshot
    return ""


def start_campaign(db: Session, *, user_id, list_id, generated_email_id, subject, from_email, from_name, html) -> EmailCampaign:
    total = db.query(Contact).filter_by(list_id=int(list_id)).count()
    camp = EmailCampaign(
        user_id=user_id, list_id=int(list_id), generated_email_id=generated_email_id,
        subject=subject, from_email=from_email, from_name=from_name,
        status="queued", total_count=total, sent_count=0,
    )
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return camp


def run_campaign(campaign_id: int) -> None:
    """Background worker: opens its own DB session, sends in batches, tracks status."""
    from app.db import SessionLocal
    db: Session = SessionLocal()
    try:
        camp = db.get(EmailCampaign, campaign_id)
        if not camp:
            return
        camp.status = "sending"
        db.commit()
        html = _campaign_html(db, camp)
        rows = [
            {"email": c.email, "first_name": c.first_name, "last_name": c.last_name}
            for c in db.query(Contact).filter_by(list_id=camp.list_id).all()
        ]
        sent = 0
        for batch in build_batches(rows):
            payload = build_mail_payload(
                batch=batch, campaign_id=camp.id, user_id=camp.user_id,
                subject=camp.subject, from_email=camp.from_email, from_name=camp.from_name, html=html,
            )
            _send_batch(payload)
            sent += len(batch)
            camp.sent_count = sent
            db.commit()
        camp.status = "sent"
        db.commit()
    except Exception as exc:
        db.rollback()
        camp = db.get(EmailCampaign, campaign_id)
        if camp:
            camp.status = "error"
            camp.error = str(exc)[:1000]
            db.commit()
    finally:
        db.close()
