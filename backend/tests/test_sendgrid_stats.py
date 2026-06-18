import httpx

from app import sendgrid_stats as ss


def _fake_client(existing_categories, stats_payload):
    """Mock httpx.Client routing by URL: /categories vs /categories/stats."""
    class _Resp:
        def __init__(self, status, data):
            self.status_code = status
            self._data = data
        def json(self):
            return self._data
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url, *a, **k):
            if url.endswith("/categories/stats"):
                return _Resp(200, stats_payload)
            if url.endswith("/categories"):
                return _Resp(200, [{"category": c} for c in existing_categories])
            return _Resp(404, {})
    return _Client


def test_fetch_sums_per_day_per_category(monkeypatch):
    payload = [
        {"date": "2026-06-17", "stats": [
            {"type": "category", "name": "campaign_2", "metrics": {
                "requests": 1, "delivered": 1, "opens": 2, "unique_opens": 1,
                "clicks": 1, "unique_clicks": 1, "bounces": 0, "spam_reports": 0, "unsubscribes": 0}},
        ]},
        {"date": "2026-06-18", "stats": [
            {"type": "category", "name": "campaign_2", "metrics": {
                "requests": 0, "delivered": 0, "opens": 3, "unique_opens": 0,
                "clicks": 0, "unique_clicks": 0, "bounces": 0, "spam_reports": 0, "unsubscribes": 0}},
        ]},
    ]
    monkeypatch.setattr(ss, "SENDGRID_API_KEY", "SG.test")
    monkeypatch.setattr(httpx, "Client", _fake_client(["campaign_2"], payload))
    res = ss.fetch_campaign_stats([2], "2026-06-17")
    assert res[2]["delivered"] == 1
    assert res[2]["opens"] == 5            # 2 + 3 summed across days
    assert res[2]["unique_opens"] == 1
    assert res[2]["unique_clicks"] == 1


def test_fetch_skips_nonexistent_categories(monkeypatch):
    """Regression: requesting a category that doesn't exist must not wipe out the rest.
    Only existing categories are queried, so unknown ids are simply absent."""
    payload = [
        {"date": "2026-06-18", "stats": [
            {"type": "category", "name": "campaign_4", "metrics": {
                "requests": 1, "delivered": 1, "opens": 1, "unique_opens": 1,
                "clicks": 2, "unique_clicks": 1, "bounces": 0, "spam_reports": 0, "unsubscribes": 0}},
        ]},
    ]
    monkeypatch.setattr(ss, "SENDGRID_API_KEY", "SG.test")
    # only campaign_4 exists; campaign_2/3 never sent with a category
    monkeypatch.setattr(httpx, "Client", _fake_client(["campaign_4"], payload))
    res = ss.fetch_campaign_stats([2, 3, 4], "2026-06-17")
    assert set(res.keys()) == {4}
    assert res[4]["unique_clicks"] == 1


def test_fetch_empty_without_key(monkeypatch):
    monkeypatch.setattr(ss, "SENDGRID_API_KEY", None)
    assert ss.fetch_campaign_stats([1], "2026-06-01") == {}
    assert ss.is_configured() is False
