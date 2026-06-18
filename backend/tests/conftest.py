import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


@pytest.fixture(autouse=True)
def _no_stats_network(monkeypatch):
    """Disable SendGrid Stats polling by default so tests never hit the network.
    Tests that exercise the polling path re-enable it explicitly."""
    from app import sendgrid_stats
    monkeypatch.setattr(sendgrid_stats, "is_configured", lambda: False)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()
