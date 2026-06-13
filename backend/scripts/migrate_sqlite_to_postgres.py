import json
import sqlite3
from datetime import datetime

from sqlalchemy import create_engine, text


TABLES = [
    "users",
    "email_verification_tokens",
    "company_profiles",
    "generation_sessions",
    "generation_jobs",
    "generation_logs",
    "generated_emails",
    "user_profiles",
    "token_ledger",
    "payment_fulfillments",
    "token_refund_requests",
    "user_sessions",
]


def _rows_from_sqlite(sqlite_path: str, table: str):
    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(f"SELECT * FROM {table}").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def _truncate_table(conn, table: str):
    conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))


def _insert_rows(conn, table: str, rows: list[dict]):
    if not rows:
        return
    cols = list(rows[0].keys())
    col_sql = ", ".join([f'"{c}"' for c in cols])
    val_sql = ", ".join([f":{c}" for c in cols])
    stmt = text(f'INSERT INTO "{table}" ({col_sql}) VALUES ({val_sql})')
    conn.execute(stmt, rows)


def migrate(sqlite_path: str, postgres_url: str):
    if not postgres_url:
        raise RuntimeError("DATABASE_URL must point to PostgreSQL for migration.")
    if "sslmode=" not in postgres_url:
        sep = "&" if "?" in postgres_url else "?"
        postgres_url = f"{postgres_url}{sep}sslmode=require"

    pg = create_engine(postgres_url, pool_pre_ping=True)
    with pg.begin() as conn:
        for t in TABLES:
            _truncate_table(conn, t)
        counts = {}
        for t in TABLES:
            rows = _rows_from_sqlite(sqlite_path, t)
            _insert_rows(conn, t, rows)
            counts[t] = len(rows)
    print(json.dumps({"ok": True, "migratedAt": datetime.utcnow().isoformat() + "Z", "counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    import os

    sqlite_file = os.getenv("SQLITE_PATH", "app.db")
    postgres = os.getenv("DATABASE_URL", "")
    migrate(sqlite_file, postgres)
