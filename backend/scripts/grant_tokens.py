"""
Grant tokens to a user (admin / support). Usage:
  python -m scripts.grant_tokens user@example.com 1000
"""
from __future__ import annotations

import sys

from app.db import SessionLocal
from app.billing import credit_tokens_idempotent
from app.models import User


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.grant_tokens <email> <tokens>")
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    tokens = int(sys.argv[2])
    db = SessionLocal()
    try:
        user = db.scalar(__import__("sqlalchemy").select(User).where(User.email == email))
        if not user:
            print("User not found:", email)
            sys.exit(1)
        ext = f"admin_grant:{email}:{tokens}"
        ok = credit_tokens_idempotent(
            db,
            user_id=user.id,
            tokens=tokens,
            external_id=ext,
            reason="admin_grant",
        )
        db.commit()
        if ok:
            print("OK: granted", tokens, "tokens to", email)
        else:
            print("Already granted with id", ext)
    finally:
        db.close()


if __name__ == "__main__":
    main()
