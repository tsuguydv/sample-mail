from app import contacts_store as cs
from app.models import Contact


def test_create_and_get_lists(db_session):
    lst = cs.create_list(db_session, user_id=1, name="VIP")
    assert lst["name"] == "VIP" and lst["contactCount"] == 0
    lists = cs.get_lists(db_session, user_id=1)
    assert any(l["id"] == lst["id"] for l in lists)


def test_import_dedup_upsert(db_session):
    lst = cs.create_list(db_session, user_id=1, name="L")
    rows = [{"email": "a@b.c", "first_name": "A"}, {"email": "a@b.c", "first_name": "A2"}]
    res = cs.import_contacts(db_session, 1, lst["id"], rows)
    assert res["uploaded"] == 2
    lists = cs.get_lists(db_session, 1)
    assert next(l for l in lists if l["id"] == lst["id"])["contactCount"] == 1  # дедуп
    c = db_session.query(Contact).filter_by(list_id=lst["id"], email="a@b.c").one()
    assert c.first_name == "A2"  # upsert обновил имя


def test_delete_list_removes_contacts(db_session):
    lst = cs.create_list(db_session, 1, "X")
    cs.import_contacts(db_session, 1, lst["id"], [{"email": "z@z.z"}])
    assert cs.delete_list(db_session, 1, lst["id"]) is True
    assert cs.get_lists(db_session, 1) == []


def test_get_contacts_returns_saved(db_session):
    lst = cs.create_list(db_session, user_id=1, name="L")
    cs.import_contacts(db_session, 1, lst["id"], [
        {"email": "a@b.c", "first_name": "A"}, {"email": "d@e.f", "first_name": "D"},
    ])
    rows = cs.get_contacts(db_session, 1, lst["id"])
    assert {r["email"] for r in rows} == {"a@b.c", "d@e.f"}
    assert rows[0]["first_name"] in ("A", "D")


def test_get_contacts_rejects_foreign_list(db_session):
    lst = cs.create_list(db_session, user_id=1, name="Owned")
    cs.import_contacts(db_session, 1, lst["id"], [{"email": "a@b.c"}])
    assert cs.get_contacts(db_session, user_id=2, list_id=lst["id"]) == []


def test_import_rejects_foreign_list(db_session):
    lst = cs.create_list(db_session, user_id=1, name="Owned")
    res = cs.import_contacts(db_session, user_id=2, list_id=lst["id"], contacts=[{"email": "a@b.c"}])
    assert res["uploaded"] == 0 and res["errors"]
