"""
Grant unlimited plan (subscriptionActive in user_profiles.settings_json).

Usage (from backend/):
  python scripts/grant_subscription.py
  python scripts/grant_subscription.py other@email.com
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# backend/ is the package root for "app"
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import User, UserProfile  # noqa: E402


def main() -> int:
    email = (sys.argv[1] if len(sys.argv) > 1 else "nikitaradchenko2@gmail.com").lower().strip()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print("User not found:", email)
            return 1
        profile = db.get(UserProfile, user.id)
        if profile is None:
            profile = UserProfile(user_id=user.id)
            db.add(profile)
        prev: dict = {}
        if profile.settings_json:
            try:
                prev = json.loads(profile.settings_json)
            except Exception:
                prev = {}
        prev["subscriptionActive"] = True
        profile.settings_json = json.dumps(prev, ensure_ascii=False)
        db.commit()
        print("OK: unlimited plan (subscriptionActive=true) for", email)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
