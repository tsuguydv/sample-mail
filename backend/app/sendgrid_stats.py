"""Poll SendGrid Stats API for per-campaign metrics by category.

Each campaign send is tagged with category `campaign_<id>` (see campaign_sender).
We then query SendGrid's category stats — this is pull-based, so it works locally
without a public URL or the Event Webhook.
"""
from __future__ import annotations

import httpx

from app.config import SENDGRID_API_KEY

_STATS_URL = "https://api.sendgrid.com/v3/categories/stats"
_CATEGORIES_URL = "https://api.sendgrid.com/v3/categories"
_CATEGORY_PREFIX = "campaign_"
_METRIC_KEYS = (
    "requests", "delivered", "opens", "unique_opens",
    "clicks", "unique_clicks", "bounces", "spam_reports", "unsubscribes",
)


def is_configured() -> bool:
    return bool(SENDGRID_API_KEY)


def _empty() -> dict:
    return {k: 0 for k in _METRIC_KEYS}


def _existing_categories(headers: dict) -> set[str]:
    """Categories that actually exist on the account.

    The stats endpoint returns 404 for the WHOLE request if any requested category
    is unknown, so we must only ask for categories that exist (campaigns sent before
    categorization, or never sent, won't have one).
    """
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(_CATEGORIES_URL, headers=headers, params={"limit": 500})
        if r.status_code == 200:
            return {str(x.get("category") or "") for x in (r.json() or [])}
    except Exception:
        pass
    return set()


def fetch_campaign_stats(campaign_ids: list[int], start_date: str) -> dict[int, dict]:
    """Return {campaign_id: {metric: total}} aggregated over the period.

    Sums per-day metrics for each existing `campaign_<id>` category. Network/auth
    errors are swallowed (returns whatever was collected) so analytics degrades
    gracefully.
    """
    if not SENDGRID_API_KEY or not campaign_ids:
        return {}
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
    existing = _existing_categories(headers)
    wanted = [cid for cid in campaign_ids if f"{_CATEGORY_PREFIX}{cid}" in existing]
    if not wanted:
        return {}
    out: dict[int, dict] = {}
    # SendGrid allows up to 10 categories per request.
    for i in range(0, len(wanted), 10):
        chunk = wanted[i:i + 10]
        params = [
            ("start_date", start_date),
            ("aggregated_by", "day"),
        ] + [("categories", f"{_CATEGORY_PREFIX}{cid}") for cid in chunk]
        try:
            with httpx.Client(timeout=25.0) as client:
                r = client.get(_STATS_URL, headers=headers, params=params)
            if r.status_code != 200:
                continue
            for day in r.json() or []:
                for stat in day.get("stats") or []:
                    name = str(stat.get("name") or "")
                    if not name.startswith(_CATEGORY_PREFIX):
                        continue
                    try:
                        cid = int(name[len(_CATEGORY_PREFIX):])
                    except ValueError:
                        continue
                    metrics = stat.get("metrics") or {}
                    acc = out.setdefault(cid, _empty())
                    for k in _METRIC_KEYS:
                        acc[k] += int(metrics.get(k) or 0)
        except Exception:
            continue
    return out
