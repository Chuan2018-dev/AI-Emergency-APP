from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen',
                risk_score REAL NOT NULL DEFAULT 0,
                account_flagged INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT,
                emergency_type TEXT NOT NULL,
                description TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                selfie_path TEXT NOT NULL,
                accident_path TEXT NOT NULL,
                lora_payload TEXT,
                severity_label TEXT NOT NULL,
                severity_confidence REAL NOT NULL,
                verification_score REAL NOT NULL,
                face_ok INTEGER NOT NULL,
                accident_image_ok INTEGER NOT NULL,
                suspicious INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                ip_address TEXT,
                device_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        # Safe, idempotent migration helpers for Phase 2 fields.
        user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "risk_score" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN risk_score REAL NOT NULL DEFAULT 0")
        if "account_flagged" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN account_flagged INTEGER NOT NULL DEFAULT 0")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat()
