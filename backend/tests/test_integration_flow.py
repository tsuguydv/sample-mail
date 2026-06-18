"""End-to-end HTTP flow through the real routes, with auth + DB dependency overrides."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app, get_current_user
from app.db import get_db, Base


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _override_db():
        yield session

    def _override_user():
        return SimpleNamespace(id=1, email="u@test.dev")

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_send_campaign_renders_from_payload_when_no_snapshot(client, monkeypatch):
    """A campaign for an email without html_snapshot must render from payload (parity
    with /api/send/generated), not fail with 'save it first'."""
    import app.main as main
    from app.models import ContactList, Contact, GeneratedEmail

    c, session = client
    lst = ContactList(user_id=1, name="L")
    session.add(lst)
    session.commit()
    session.add(Contact(list_id=lst.id, user_id=1, email="a@b.c"))
    ge = GeneratedEmail(user_id=1, subject="Hi", title="t", template_id="t1",
                        payload_json='{"sessionId": "sess1"}', html_snapshot="")
    session.add(ge)
    session.commit()
    ge_id = ge.id

    monkeypatch.setattr(main, "api_export", lambda req, user, db: {"html": "<p>rendered</p>"})

    r = c.post("/api/contacts/send-campaign", json={
        "list_id": str(lst.id), "list_name": "L", "generated_email_id": ge_id, "subject": "Hi",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] in ("queued", "sending", "sent")
    # the rendered HTML must be persisted so the background sender can use it
    session.refresh(ge)
    assert ge.html_snapshot == "<p>rendered</p>"


def test_upload_accepts_numeric_list_id(client):
    """Frontend sends list_id as a NUMBER (DB id from JSON); upload must accept it."""
    c, session = client
    list_id = c.post("/api/contacts/lists", json={"name": "Nums"}).json()["id"]
    # list_id sent as int, exactly like the browser does
    r = c.post("/api/contacts/upload", json={"lists": [{
        "list_id": list_id, "list_name": "Nums", "contacts": [{"email": "x@y.z"}],
    }]})
    assert r.status_code == 200, r.text
    assert r.json()[0]["uploaded_contacts"] == 1
    lst = next(l for l in c.get("/api/contacts/lists").json()["lists"] if l["id"] == list_id)
    assert lst["contactCount"] == 1


def test_get_list_contacts_route(client):
    c, session = client
    list_id = c.post("/api/contacts/lists", json={"name": "L"}).json()["id"]
    c.post("/api/contacts/upload", json={"lists": [{
        "list_id": list_id, "list_name": "L",
        "contacts": [{"email": "a@b.c", "first_name": "A"}, {"email": "d@e.f"}],
    }]})
    r = c.get(f"/api/contacts/lists/{list_id}/contacts")
    assert r.status_code == 200, r.text
    emails = {x["email"] for x in r.json()["contacts"]}
    assert emails == {"a@b.c", "d@e.f"}


def test_full_contacts_flow(client):
    c, session = client

    # 1) create list
    r = c.post("/api/contacts/lists", json={"name": "VIP"})
    assert r.status_code == 200, r.text
    list_id = r.json()["id"]

    # 2) upload contacts
    payload = {"lists": [{
        "list_id": str(list_id), "list_name": "VIP",
        "contacts": [{"email": "a@b.c", "first_name": "A"}, {"email": "d@e.f"}],
    }]}
    r = c.post("/api/contacts/upload", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()[0]["uploaded_contacts"] == 2

    # 3) list shows contactCount
    r = c.get("/api/contacts/lists")
    assert r.status_code == 200
    lst = next(l for l in r.json()["lists"] if l["id"] == list_id)
    assert lst["contactCount"] == 2

    # 4) seed a campaign directly, post webhook events for it
    from app.models import EmailCampaign
    camp = EmailCampaign(user_id=1, list_id=list_id, subject="Hello", status="sent", total_count=2, sent_count=2)
    session.add(camp)
    session.commit()
    events = [
        {"sg_event_id": "i1", "event": "delivered", "email": "a@b.c", "campaign_id": str(camp.id), "timestamp": 1700000000},
        {"sg_event_id": "i2", "event": "delivered", "email": "d@e.f", "campaign_id": str(camp.id), "timestamp": 1700000000},
        {"sg_event_id": "i3", "event": "open", "email": "a@b.c", "campaign_id": str(camp.id), "timestamp": 1700000001},
    ]
    r = c.post("/api/webhooks/sendgrid/events", json=events)
    assert r.status_code == 200 and r.json()["stored"] == 3

    # 5) analytics reflects the events
    r = c.get("/api/analytics/campaigns")
    assert r.status_code == 200, r.text
    camps = r.json()["campaigns"]
    row = next(x for x in camps if x["id"] == str(camp.id))
    assert row["delivered"] == 2 and row["unique_opens"] == 1
    assert row["open_rate"] == 50.0

    # 6) delete list removes it
    r = c.delete(f"/api/contacts/lists/{list_id}")
    assert r.status_code == 200
    r = c.get("/api/contacts/lists")
    assert all(l["id"] != list_id for l in r.json()["lists"])
