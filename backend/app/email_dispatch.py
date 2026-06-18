"""
Email provider dispatch: routes sending, sender verification, contact lists,
contact import, campaigns and stats to UniSender or SendGrid based on
EMAIL_PROVIDER. Public functions keep provider-agnostic shapes so main.py and the
frontend contracts stay unchanged.

On the SendGrid provider, contacts/campaigns/analytics run on the Email API
(`/v3/mail/send`) + local DB + Event Webhook (see contacts_store, campaign_sender,
sendgrid_events) — not the Marketing API. Transactional send / sender verification
use SendGrid directly here.
"""

from __future__ import annotations

import re

import httpx
from fastapi import HTTPException

from app.config import (
    EMAIL_PROVIDER,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
    UNISENDER_FROM_EMAIL,
    UNISENDER_FROM_NAME,
)
from app import unisender_client
from app import contacts_store
from app.schemas import CampaignStatItem


def system_sender() -> tuple[str, str]:
    """Default system sender (email, name) for transactional mail like verification."""
    if EMAIL_PROVIDER == "unisender":
        return (UNISENDER_FROM_EMAIL or "", UNISENDER_FROM_NAME or "")
    return (SENDGRID_FROM_EMAIL or "", "")


# ----------------------------- SendGrid transactional -----------------------------

def _sendgrid_send_email(*, from_email: str, from_name: str, to_email: str, subject: str, html: str, text: str = "") -> None:
    if not SENDGRID_API_KEY:
        raise HTTPException(status_code=500, detail="SendGrid is not configured")
    if not from_email:
        raise HTTPException(status_code=400, detail="Sender email is required")
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": from_name or from_email},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text or re.sub("<[^>]+>", " ", html or "").strip()},
            {"type": "text/html", "value": html or ""},
        ],
    }
    with httpx.Client(timeout=15.0) as client:
        res = client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"SendGrid send failed: {res.status_code} {res.text[:300]}")


def _sendgrid_sender_is_verified(sender_email: str) -> bool:
    if not SENDGRID_API_KEY or not sender_email:
        return False
    sender_email = sender_email.lower().strip()
    sender_domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
    with httpx.Client(timeout=15.0) as client:
        s_res = client.get("https://api.sendgrid.com/v3/verified_senders", headers=headers)
        if s_res.status_code < 400:
            for item in (s_res.json() or {}).get("results") or []:
                if str(item.get("from_email") or "").lower().strip() == sender_email and bool(item.get("verified")):
                    return True
        d_res = client.get("https://api.sendgrid.com/v3/whitelabel/domains", headers=headers)
        if d_res.status_code < 400:
            for dom in d_res.json() or []:
                if sender_domain and sender_domain == str(dom.get("domain") or "").lower().strip() and bool(dom.get("valid")):
                    return True
    return False


# ----------------------------- Public dispatch -----------------------------

def send_email(*, from_email: str, from_name: str, to_email: str, subject: str, html: str, text: str = "") -> None:
    if EMAIL_PROVIDER == "unisender":
        try:
            unisender_client.send_email(
                from_email=from_email, from_name=from_name, to_email=to_email,
                subject=subject, html=html, text=text,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"UniSender send failed: {exc}")
        return
    _sendgrid_send_email(from_email=from_email, from_name=from_name, to_email=to_email, subject=subject, html=html, text=text)


def sender_is_verified(sender_email: str) -> bool:
    if EMAIL_PROVIDER == "unisender":
        return unisender_client.sender_is_verified(sender_email)
    return _sendgrid_sender_is_verified(sender_email)


def get_lists(db=None, user_id=None) -> list[dict]:
    if EMAIL_PROVIDER == "unisender":
        try:
            return unisender_client.get_lists()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"UniSender error: {exc}")
    return contacts_store.get_lists(db, user_id)


def get_contacts(list_id, db=None, user_id=None) -> list[dict]:
    if EMAIL_PROVIDER == "unisender":
        return []  # not supported on UniSender (contacts live in UniSender lists)
    return contacts_store.get_contacts(db, user_id, int(list_id))


def create_list(name: str, db=None, user_id=None) -> dict:
    if EMAIL_PROVIDER == "unisender":
        raise HTTPException(status_code=400, detail="List management is available on the SendGrid provider")
    return contacts_store.create_list(db, user_id, name)


def delete_list(list_id, db=None, user_id=None) -> bool:
    if EMAIL_PROVIDER == "unisender":
        raise HTTPException(status_code=400, detail="List management is available on the SendGrid provider")
    return contacts_store.delete_list(db, user_id, int(list_id))


def import_contacts(list_id: str, contacts: list[dict], db=None, user_id=None) -> dict:
    if EMAIL_PROVIDER == "unisender":
        try:
            return unisender_client.import_contacts(list_id, contacts)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"UniSender error: {exc}")
    return contacts_store.import_contacts(db, user_id, int(list_id), contacts)


def send_campaign(*, list_id: str, subject: str, from_email: str, from_name: str, html: str,
                  db=None, user_id=None, generated_email_id=None) -> dict:
    if EMAIL_PROVIDER == "unisender":
        try:
            return unisender_client.send_campaign(
                list_id=list_id, subject=subject, from_email=from_email, from_name=from_name, html=html,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"UniSender campaign failed: {exc}")
    from app import campaign_sender
    camp = campaign_sender.start_campaign(
        db, user_id=user_id, list_id=list_id, generated_email_id=generated_email_id,
        subject=subject, from_email=from_email, from_name=from_name, html=html,
    )
    return {"id": camp.id, "status": camp.status, "name": subject, "_run": camp.id}


def campaign_stats(db=None, user_id=None) -> list[CampaignStatItem]:
    if EMAIL_PROVIDER == "unisender":
        try:
            rows = unisender_client.get_campaign_stats()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"UniSender stats error: {exc}")
        return [CampaignStatItem(**row) for row in rows]
    from app import sendgrid_events
    return [CampaignStatItem(**row) for row in sendgrid_events.aggregate_stats(db, user_id)]
