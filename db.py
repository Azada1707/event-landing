"""Database access layer for the event registration app.

Stores registrations in a local SQLite database. All queries are
parameterised to prevent SQL injection. Personal data (name, phone, email,
etc.) is stored in plaintext because it must be retrievable for guest-list
export and CRM integration; production deployments should additionally
restrict filesystem access to the DB and, where required by policy, encrypt
fields at rest.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.environ.get("EVENT_DB_PATH", str(DATA_DIR / "registrations.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    company       TEXT NOT NULL,
    position      TEXT NOT NULL,
    phone         TEXT NOT NULL,
    email         TEXT NOT NULL,
    comments      TEXT NOT NULL DEFAULT '',
    consent       INTEGER NOT NULL CHECK (consent IN (0, 1)),
    photo_consent INTEGER NOT NULL DEFAULT 0 CHECK (photo_consent IN (0, 1)),
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_registrations_email ON registrations (email);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Migrate pre-existing databases that lack the photo_consent column.
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(registrations)").fetchall()
        }
        if "photo_consent" not in cols:
            conn.execute(
                "ALTER TABLE registrations "
                "ADD COLUMN photo_consent INTEGER NOT NULL DEFAULT 0 "
                "CHECK (photo_consent IN (0, 1))"
            )


def insert_registration(data: dict) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO registrations
                (first_name, last_name, company, position, phone, email,
                 comments, consent, photo_consent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["first_name"],
                data["last_name"],
                data["company"],
                data["position"],
                data["phone"],
                data["email"],
                data.get("comments", ""),
                1 if data.get("consent") else 0,
                1 if data.get("photo_consent") else 0,
                now,
            ),
        )
        return cur.lastrowid


def email_exists(email: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM registrations WHERE lower(email) = lower(?) LIMIT 1",
            (email,),
        ).fetchone()
        return row is not None


def list_registrations() -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM registrations ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return rows