from app import sendgrid_events as se
from app.models import ContactList, EmailCampaign, EmailEvent


def test_aggregate(db_session):
    lst = ContactList(user_id=1, name="L")
    db_session.add(lst)
    db_session.commit()
    camp = EmailCampaign(user_id=1, list_id=lst.id, subject="S", status="sent", total_count=2, sent_count=2)
    db_session.add(camp)
    db_session.commit()
    evs = [("delivered", "a@b.c"), ("delivered", "d@e.f"), ("open", "a@b.c"), ("open", "a@b.c"), ("click", "a@b.c")]
    for i, (t, em) in enumerate(evs):
        db_session.add(EmailEvent(campaign_id=camp.id, email=em, event_type=t, sg_event_id=f"e{i}"))
    db_session.commit()

    rows = se.aggregate_stats(db_session, 1)
    assert len(rows) == 1
    r = rows[0]
    assert r["requests"] == 2 and r["delivered"] == 2
    assert r["opens"] == 2 and r["unique_opens"] == 1
    assert r["unique_clicks"] == 1
    assert r["open_rate"] == 50.0  # 1 unique open / 2 delivered


def test_aggregate_combines_polling_and_events_by_max(db_session, monkeypatch):
    from app import sendgrid_stats
    lst = ContactList(user_id=1, name="L"); db_session.add(lst); db_session.commit()
    camp = EmailCampaign(user_id=1, list_id=lst.id, subject="S", status="sent", total_count=5)
    db_session.add(camp); db_session.commit()
    # webhook gave 1 delivered; polling reports more — analytics should take the max
    db_session.add(EmailEvent(campaign_id=camp.id, email="a@b.c", event_type="delivered", sg_event_id="e0"))
    db_session.commit()
    monkeypatch.setattr(sendgrid_stats, "is_configured", lambda: True)
    monkeypatch.setattr(sendgrid_stats, "fetch_campaign_stats",
                        lambda ids, start: {camp.id: {"requests": 5, "delivered": 5,
                                                      "unique_opens": 3, "unique_clicks": 2,
                                                      "opens": 4, "clicks": 2, "bounces": 0,
                                                      "spam_reports": 0, "unsubscribes": 0}})
    r = se.aggregate_stats(db_session, 1)[0]
    assert r["requests"] == 5
    assert r["delivered"] == 5           # max(1 event, 5 polled)
    assert r["unique_opens"] == 3
    assert r["open_rate"] == 60.0        # 3/5


def test_aggregate_scopes_to_user(db_session):
    other = ContactList(user_id=99, name="X")
    db_session.add(other)
    db_session.commit()
    db_session.add(EmailCampaign(user_id=99, list_id=other.id, subject="S", status="sent", total_count=1))
    db_session.commit()
    assert se.aggregate_stats(db_session, 1) == []
