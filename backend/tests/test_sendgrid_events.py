from app import sendgrid_events as se


def test_store_events_idempotent(db_session):
    events = [
        {"sg_event_id": "e1", "event": "open", "email": "a@b.c", "campaign_id": "5", "timestamp": 1700000000},
        {"sg_event_id": "e1", "event": "open", "email": "a@b.c", "campaign_id": "5", "timestamp": 1700000000},
        {"sg_event_id": "e2", "event": "click", "email": "a@b.c", "campaign_id": "5", "timestamp": 1700000001},
    ]
    n = se.store_events(db_session, events)
    assert n == 2  # дубль e1 пропущен
    n2 = se.store_events(db_session, events)
    assert n2 == 0  # повторный вызов ничего не добавляет


def test_store_skips_without_campaign(db_session):
    n = se.store_events(db_session, [{"sg_event_id": "x", "event": "open", "email": "a@b.c"}])
    assert n == 0  # нет campaign_id → пропуск


def test_verify_signature_rejects_empty():
    assert se.verify_signature("", b"{}", "sig", "123") is False
    assert se.verify_signature("key", b"{}", "", "") is False
