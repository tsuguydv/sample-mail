"""
UniSender API client (https://www.unisender.com/ru/support/api/).

All methods POST to {UNISENDER_BASE_URL}/<method> with `format=json` and `api_key`.
Responses are `{"result": ...}` on success or `{"error": "...", "code": "..."}` on failure.
"""

from __future__ import annotations

import re

import httpx

from app.config import (
    UNISENDER_API_KEY,
    UNISENDER_BASE_URL,
    UNISENDER_LIST_ID,
)


def _call(method: str, params: list[tuple] | None = None) -> dict:
    """POST a UniSender API call. `params` is a list of (key, value) tuples
    (UniSender uses PHP-style array keys like `data[0][1]`)."""
    body: list[tuple] = [("format", "json"), ("api_key", UNISENDER_API_KEY or "")]
    if params:
        body.extend((k, v) for k, v in params if v is not None)
    resp = httpx.post(f"{UNISENDER_BASE_URL}/{method}", data=body, timeout=60.0)
    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"UniSender {method}: bad response {resp.status_code} {resp.text[:200]}") from exc
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"UniSender {method}: {data.get('error')} (code={data.get('code')})")
    return data.get("result") if isinstance(data, dict) else data


def _strip_html(html: str) -> str:
    return re.sub("<[^>]+>", " ", html or "").strip()


def send_email(*, from_email: str, from_name: str, to_email: str, subject: str, html: str, text: str = "") -> None:
    """Transactional single send via `sendEmail` (requires a list_id for the unsubscribe link)."""
    list_id = UNISENDER_LIST_ID
    if not list_id:
        # sendEmail mandates a list for the unsubscribe link; use the first available list.
        lists = get_lists()
        if lists:
            list_id = str(lists[0]["id"])
    if not list_id:
        raise RuntimeError("UNISENDER_LIST_ID is not set and no lists exist in the account")
    _call(
        "sendEmail",
        [
            ("email", to_email),
            ("sender_name", from_name or from_email),
            ("sender_email", from_email),
            ("subject", subject),
            ("body", html or ""),
            ("list_id", str(list_id)),
            ("lang", "ru"),
            ("error_checking", "1"),
        ],
    )


def sender_is_verified(sender_email: str) -> bool:
    """UniSender has no public 'verified senders' lookup like SendGrid; the platform
    rejects unconfirmed senders at send time. For MVP we treat any non-empty sender as OK."""
    return bool((sender_email or "").strip())


def get_lists() -> list[dict]:
    """Return contact lists as [{id, name, contactCount}]."""
    result = _call("getLists", []) or []
    out = []
    for l in result:
        if not isinstance(l, dict):
            continue
        out.append({"id": l.get("id"), "name": l.get("title") or "", "contactCount": None})
    return out


def import_contacts(list_id: str, contacts: list[dict]) -> dict:
    """Bulk import contacts (subscribing them to list_id) via `importContacts`, in batches of 500.

    Each contact dict: {email, first_name, last_name, city, country}. Only email, a combined
    Name, and the list subscription are sent (UniSender ignores undefined custom fields)."""
    uploaded = 0
    batches = 0
    errors: list[dict] = []
    field_names = [
        ("field_names[0]", "email"),
        ("field_names[1]", "Name"),
        ("field_names[2]", "email_list_ids"),
    ]
    chunk = 500
    for i in range(0, len(contacts), chunk):
        batch = contacts[i : i + chunk]
        rows: list[tuple] = list(field_names)
        for ri, c in enumerate(batch):
            email = str(c.get("email") or "").strip()
            if not email:
                continue
            name = (str(c.get("first_name") or "").strip() + " " + str(c.get("last_name") or "").strip()).strip()
            rows.append((f"data[{ri}][0]", email))
            rows.append((f"data[{ri}][1]", name))
            rows.append((f"data[{ri}][2]", str(list_id)))
        batches += 1
        try:
            res = _call("importContacts", rows) or {}
            uploaded += int(res.get("inserted", 0) or 0) + int(res.get("updated", 0) or 0)
            log = res.get("log") or []
            for entry in log:
                if isinstance(entry, dict) and entry.get("message"):
                    errors.append({"status": entry.get("code", "warn"), "body": str(entry.get("message"))[:500]})
        except Exception as exc:
            errors.append({"status": "exception", "body": str(exc)[:500]})
    return {"uploaded": uploaded, "batches": batches, "errors": errors}


def send_campaign(*, list_id: str, subject: str, from_email: str, from_name: str, html: str) -> dict:
    """Create an email message and launch a campaign to the given list.
    Returns {id, status, name}."""
    msg = _call(
        "createEmailMessage",
        [
            ("sender_name", from_name or from_email),
            ("sender_email", from_email),
            ("subject", subject),
            ("body", html or ""),
            ("list_id", str(list_id)),
            ("lang", "ru"),
        ],
    ) or {}
    message_id = msg.get("message_id")
    if not message_id:
        raise RuntimeError("UniSender createEmailMessage returned no message_id")
    camp = _call("createCampaign", [("message_id", str(message_id))]) or {}
    campaign_id = camp.get("campaign_id")
    return {
        "id": str(campaign_id or message_id),
        "status": str(camp.get("status") or "scheduled"),
        "name": subject,
    }


def get_campaign_stats() -> list[dict]:
    """List campaigns and their aggregate stats, mapped to CampaignStatItem fields."""
    campaigns = _call("getCampaigns", [("limit", "50")]) or []
    out: list[dict] = []
    for camp in campaigns:
        if not isinstance(camp, dict):
            continue
        cid = camp.get("id")
        if cid is None:
            continue
        try:
            stats = _call("getCampaignCommonStats", [("campaign_id", str(cid))]) or {}
        except Exception:
            stats = {}
        sent = int(stats.get("sent", 0) or 0)
        delivered = int(stats.get("delivered", 0) or 0)
        unique_opens = int(stats.get("read_unique", 0) or 0)
        unique_clicks = int(stats.get("clicked_unique", 0) or 0)
        base = delivered or sent
        out.append({
            "id": str(cid),
            "name": camp.get("subject") or camp.get("name") or f"Кампания {cid}",
            "status": str(camp.get("status") or ""),
            "send_at": camp.get("start_time") or camp.get("created"),
            "requests": sent,
            "delivered": delivered,
            "opens": int(stats.get("read_all", 0) or 0),
            "unique_opens": unique_opens,
            "clicks": int(stats.get("clicked_all", 0) or 0),
            "unique_clicks": unique_clicks,
            "bounces": int(stats.get("undeliverable", 0) or stats.get("error", 0) or 0),
            "unsubscribes": int(stats.get("unsubscribed", 0) or 0),
            "spam_reports": int(stats.get("spam", 0) or stats.get("spam_complaint", 0) or 0),
            "open_rate": round(unique_opens / base * 100, 1) if base else 0.0,
            "click_rate": round(unique_clicks / base * 100, 1) if base else 0.0,
        })
    return out
