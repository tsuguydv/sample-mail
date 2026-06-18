import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ContactList, Contact, EmailCampaign, EmailEvent


def test_contact_unique_per_list(db_session):
    lst = ContactList(user_id=1, name="A")
    db_session.add(lst)
    db_session.commit()
    db_session.add(Contact(list_id=lst.id, user_id=1, email="x@y.z"))
    db_session.commit()
    db_session.add(Contact(list_id=lst.id, user_id=1, email="x@y.z"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_event_idempotent(db_session):
    db_session.add(EmailEvent(campaign_id=1, email="a@b.c", event_type="open", sg_event_id="evt1"))
    db_session.commit()
    db_session.add(EmailEvent(campaign_id=1, email="a@b.c", event_type="open", sg_event_id="evt1"))
    with pytest.raises(IntegrityError):
        db_session.commit()
