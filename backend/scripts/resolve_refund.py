"""
Resolve a pending token refund request (admin).
  python -m scripts.resolve_refund <request_id> approve|deny [note]
"""
from __future__ import annotations

import sys

from app.db import SessionLocal
from app.billing import resolve_refund_request


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.resolve_refund <request_id> approve|deny [admin_note]")
        sys.exit(1)
    rid = int(sys.argv[1])
    action = sys.argv[2].strip().lower()
    note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
    approve = action in ("approve", "yes", "y", "1", "true")
    db = SessionLocal()
    try:
        row = resolve_refund_request(db, request_id=rid, approve=approve, admin_note=note)
        db.commit()
        print(f"OK: request {row.id} -> {row.status}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
