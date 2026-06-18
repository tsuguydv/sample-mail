"""SendGrid Event Webhook: verify signature, store events idempotently, aggregate stats."""
from __future__ import annotations

import datetime as _dt

from sqlalchemy.orm import Session

from app.models import EmailEvent


def verify_signature(public_key_b64: str, payload_bytes: bytes, signature: str, timestamp: str) -> bool:
    """Verify SendGrid Signed Event Webhook (ECDSA). Returns True if valid.

    Mirrors SendGrid's official helper: the signed message is `timestamp + payload`,
    and the public key (base64 DER) is wrapped in a PEM envelope.
    """
    if not public_key_b64 or not signature or not timestamp:
        return False
    try:
        from ellipticcurve.ecdsa import Ecdsa
        from ellipticcurve.publicKey import PublicKey
        from ellipticcurve.signature import Signature
        pub = PublicKey.fromPem(
            "-----BEGIN PUBLIC KEY-----\n" + public_key_b64 + "\n-----END PUBLIC KEY-----"
        )
        message = timestamp + payload_bytes.decode("utf-8")
        return Ecdsa.verify(message, Signature.fromBase64(signature), pub)
    except Exception:
        return False


def aggregate_stats(db: Session, user_id: int) -> list[dict]:
    """Per-campaign CampaignStatItem dicts, combining two sources by max-per-metric:
    SendGrid Stats API polling (works locally, no webhook) and stored email_events
    (webhook; realtime on a public deployment). Usually only one source is populated,
    so max avoids double counting while keeping both paths working."""
    from app.models import EmailCampaign
    from app import sendgrid_stats
    camps = (
        db.query(EmailCampaign)
        .filter_by(user_id=user_id)
        .order_by(EmailCampaign.created_at.desc())
        .all()
    )
    if not camps:
        return []

    # Polling source: pull category stats since the earliest campaign.
    start_date = _earliest_date([c.created_at for c in camps])
    polled = sendgrid_stats.fetch_campaign_stats([c.id for c in camps], start_date) \
        if sendgrid_stats.is_configured() else {}

    out: list[dict] = []
    for camp in camps:
        evs = db.query(EmailEvent).filter_by(campaign_id=camp.id).all()

        def emails(t):
            return {e.email for e in evs if e.event_type == t}

        def count(t):
            return sum(1 for e in evs if e.event_type == t)

        p = polled.get(camp.id, {})

        def mx(metric, ev_value):
            return max(int(ev_value), int(p.get(metric, 0)))

        requests = max(camp.total_count, int(p.get("requests", 0)))
        delivered = mx("delivered", len(emails("delivered")))
        unique_opens = mx("unique_opens", len(emails("open")))
        unique_clicks = mx("unique_clicks", len(emails("click")))
        base = delivered or requests
        send_at = camp.created_at.isoformat() if hasattr(camp.created_at, "isoformat") else (
            str(camp.created_at) if camp.created_at else None
        )
        out.append({
            "id": str(camp.id),
            "name": camp.subject or f"Campaign {camp.id}",
            "status": camp.status,
            "send_at": send_at,
            "requests": requests,
            "delivered": delivered,
            "opens": mx("opens", count("open")),
            "unique_opens": unique_opens,
            "clicks": mx("clicks", count("click")),
            "unique_clicks": unique_clicks,
            "bounces": mx("bounces", count("bounce")),
            "unsubscribes": mx("unsubscribes", count("unsubscribe") + count("group_unsubscribe")),
            "spam_reports": mx("spam_reports", count("spamreport")),
            "open_rate": round(unique_opens / base * 100, 1) if base else 0.0,
            "click_rate": round(unique_clicks / base * 100, 1) if base else 0.0,
        })
    return out


def _earliest_date(values: list) -> str:
    import datetime as _dt
    dates = []
    for v in values:
        if v is None:
            continue
        dates.append(v.date().isoformat() if hasattr(v, "date") else str(v)[:10])
    return min(dates) if dates else (_dt.date.today() - _dt.timedelta(days=90)).isoformat()


def store_events(db: Session, events: list[dict]) -> int:
    written = 0
    for ev in events:
        sg_id = ev.get("sg_event_id")
        camp = ev.get("campaign_id")
        if not sg_id or not camp:
            continue
        if db.query(EmailEvent).filter_by(sg_event_id=sg_id).first():
            continue
        ts = ev.get("timestamp")
        occurred = (
            _dt.datetime.fromtimestamp(ts, _dt.timezone.utc)
            if isinstance(ts, (int, float))
            else _dt.datetime.now(_dt.timezone.utc)
        )
        db.add(EmailEvent(
            campaign_id=int(camp), email=(ev.get("email") or ""),
            event_type=(ev.get("event") or ""), sg_event_id=str(sg_id), occurred_at=occurred,
        ))
        try:
            db.commit()
            written += 1
        except Exception:
            db.rollback()
    return written
