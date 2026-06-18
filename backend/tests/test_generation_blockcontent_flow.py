"""Export render via a saved session must not leak example placeholder images."""
import json
import re
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


def test_export_test_template_has_no_placeholder_images(client):
    from app.models import GenerationSession

    c, session = client
    layout = [{"name": n, "context": {}} for n in ["header", "hero", "hero_split", "text", "cta", "footer"]]
    gen = {
        "sessionId": "sess1",
        "templateId": "user:1",
        "isModular": True,
        "blockLayout": layout,
        "blockContent": {},
        "subject": "Запуск нового продукта",
        "colorScheme": "light",
        "language": "ru",
        "imageOptions": [{"id": "img1", "url": "https://r2.example/REAL.jpg", "alt": "x"}],
        "textOptions": [{"id": "txt1", "html": "<p>Реальный текст письма.</p>"}],
        "ctaOptions": [{"id": "cta1", "label": "Купить", "href": "https://acme.io"}],
    }
    session.add(GenerationSession(session_id="sess1", user_id=1, generation_json=json.dumps(gen, ensure_ascii=False)))
    session.commit()

    r = c.post("/api/export", json={"session_id": "sess1"})
    assert r.status_code == 200, r.text
    html = r.json()["html"]
    assert not re.search(r"via\.placeholder\.com|placehold\.co", html)
    assert html.count("REAL.jpg") >= 2  # hero и hero_split
