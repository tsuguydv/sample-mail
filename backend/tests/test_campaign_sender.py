from app import campaign_sender as csnd
from app.models import ContactList, Contact, EmailCampaign


def test_build_batches():
    rows = [{"email": f"u{i}@x.com"} for i in range(2500)]
    batches = csnd.build_batches(rows, size=1000)
    assert [len(b) for b in batches] == [1000, 1000, 500]


def test_payload_has_asm_customargs_tracking(monkeypatch):
    monkeypatch.setattr(csnd, "SENDGRID_ASM_GROUP_ID", 42)
    p = csnd.build_mail_payload(
        batch=[{"email": "a@b.c", "first_name": "A"}],
        campaign_id=7, user_id=1, subject="Hi", from_email="s@d.com", from_name="S", html="<p>x</p>",
    )
    assert p["asm"] == {"group_id": 42}
    assert p["personalizations"][0]["custom_args"] == {"campaign_id": "7", "user_id": "1"}
    assert p["personalizations"][0]["to"][0]["email"] == "a@b.c"
    assert p["tracking_settings"]["open_tracking"]["enable"] is True
    assert p["tracking_settings"]["click_tracking"]["enable"] is True
    assert p["from"] == {"email": "s@d.com", "name": "S"}
    assert p["categories"] == ["campaign_7"]


def test_payload_no_asm_when_unset(monkeypatch):
    monkeypatch.setattr(csnd, "SENDGRID_ASM_GROUP_ID", None)
    p = csnd.build_mail_payload(
        batch=[{"email": "a@b.c"}], campaign_id=1, user_id=1,
        subject="S", from_email="s@d.com", from_name="", html="<p>x</p>",
    )
    assert "asm" not in p
    assert p["from"]["name"] == "s@d.com"  # fallback to from_email


def test_start_campaign_counts_contacts(db_session):
    lst = ContactList(user_id=1, name="L")
    db_session.add(lst)
    db_session.commit()
    for i in range(3):
        db_session.add(Contact(list_id=lst.id, user_id=1, email=f"u{i}@x.com"))
    db_session.commit()
    camp = csnd.start_campaign(
        db_session, user_id=1, list_id=lst.id, generated_email_id=None,
        subject="Hi", from_email="s@d.com", from_name="S", html="",
    )
    assert isinstance(camp, EmailCampaign)
    assert camp.total_count == 3 and camp.status == "queued"
