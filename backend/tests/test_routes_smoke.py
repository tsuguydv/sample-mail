from fastapi.testclient import TestClient

from app.main import app


def test_routes_exist():
    paths = {r.path for r in app.routes}
    assert "/api/webhooks/sendgrid/events" in paths
    assert "/api/contacts/lists" in paths
    assert "/api/contacts/lists/{list_id}" in paths


def test_lists_requires_auth():
    c = TestClient(app)
    r = c.get("/api/contacts/lists")
    assert r.status_code in (401, 403)
