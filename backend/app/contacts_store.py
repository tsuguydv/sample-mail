"""Local DB store for contact lists/contacts (Email-API path, replaces Marketing API)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Contact, ContactList


def get_lists(db: Session, user_id: int) -> list[dict]:
    rows = db.execute(
        select(ContactList.id, ContactList.name, func.count(Contact.id))
        .outerjoin(Contact, Contact.list_id == ContactList.id)
        .where(ContactList.user_id == user_id)
        .group_by(ContactList.id)
        .order_by(ContactList.created_at.desc())
    ).all()
    return [{"id": r[0], "name": r[1], "contactCount": int(r[2] or 0)} for r in rows]


def get_contacts(db: Session, user_id: int, list_id: int, limit: int = 500) -> list[dict]:
    lst = db.get(ContactList, int(list_id))
    if not lst or lst.user_id != user_id:
        return []
    rows = (
        db.query(Contact)
        .filter(Contact.list_id == lst.id)
        .order_by(Contact.id)
        .limit(limit)
        .all()
    )
    return [
        {"email": c.email, "first_name": c.first_name, "last_name": c.last_name,
         "city": c.city, "country": c.country}
        for c in rows
    ]


def create_list(db: Session, user_id: int, name: str) -> dict:
    lst = ContactList(user_id=user_id, name=(name or "Untitled").strip()[:200] or "Untitled")
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return {"id": lst.id, "name": lst.name, "contactCount": 0}


def delete_list(db: Session, user_id: int, list_id: int) -> bool:
    lst = db.get(ContactList, list_id)
    if not lst or lst.user_id != user_id:
        return False
    db.query(Contact).filter(Contact.list_id == list_id).delete()
    db.delete(lst)
    db.commit()
    return True


def import_contacts(db: Session, user_id: int, list_id: int, contacts: list[dict]) -> dict:
    lst = db.get(ContactList, int(list_id))
    if not lst or lst.user_id != user_id:
        return {"uploaded": 0, "batches": 0, "errors": [{"status": 404, "body": "list not found"}]}
    uploaded = 0
    for c in contacts:
        email = (c.get("email") or "").strip().lower()
        if not email:
            continue
        existing = db.query(Contact).filter_by(list_id=lst.id, email=email).one_or_none()
        if existing:
            existing.first_name = c.get("first_name") or existing.first_name
            existing.last_name = c.get("last_name") or existing.last_name
            existing.city = c.get("city") or existing.city
            existing.country = c.get("country") or existing.country
        else:
            db.add(Contact(
                list_id=lst.id, user_id=user_id, email=email,
                first_name=c.get("first_name") or "", last_name=c.get("last_name") or "",
                city=c.get("city") or "", country=c.get("country") or "",
            ))
        uploaded += 1
    db.commit()
    return {"uploaded": uploaded, "batches": 1, "errors": []}
