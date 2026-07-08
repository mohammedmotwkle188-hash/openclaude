"""Simple local memory: SQLite chat history + a small key/value fact store + reminders.

No passphrase/encryption by default (the old build's encryption added friction without
much benefit on a single-user personal machine). The DB lives at
~/.jarvis_agi/memory.db. If you want encryption later, wrap the body columns.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Dict, List, Optional

from config import APP_DIR

DB_FILE = APP_DIR / "memory.db"
_conn: Optional[sqlite3.Connection] = None


def _now() -> int:
    return int(time.time() * 1000)


def init_db() -> None:
    global _conn
    APP_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, role TEXT, body TEXT, provider TEXT, timestamp INTEGER
        );
        CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, body TEXT, updated_at INTEGER);
        CREATE TABLE IF NOT EXISTS reminders (id TEXT PRIMARY KEY, text TEXT, due_at INTEGER, done INTEGER DEFAULT 0);
        """
    )
    _conn.commit()


def _db() -> sqlite3.Connection:
    if _conn is None:
        init_db()
    return _conn  # type: ignore[return-value]


def save_message(role: str, text: str, provider: Optional[str] = None) -> None:
    _db().execute(
        "INSERT INTO messages (id, role, body, provider, timestamp) VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), role, text, provider, _now()),
    )
    _db().commit()


def load_history(limit: int = 200) -> List[Dict]:
    rows = _db().execute(
        "SELECT id, role, body, provider, timestamp FROM messages ORDER BY timestamp ASC LIMIT ?", (limit,)
    ).fetchall()
    return [{"id": r[0], "role": r[1], "text": r[2], "provider": r[3], "timestamp": r[4]} for r in rows]


def clear_history() -> None:
    _db().execute("DELETE FROM messages")
    _db().commit()


def remember_fact(key: str, value: str) -> None:
    _db().execute(
        "INSERT INTO facts (key, body, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
        (key, value, _now()),
    )
    _db().commit()


def recall_facts() -> Dict[str, str]:
    return {k: v for k, v in _db().execute("SELECT key, body FROM facts").fetchall()}


def add_reminder(text: str, due_at: int) -> Dict:
    rid = str(uuid.uuid4())
    _db().execute("INSERT INTO reminders (id, text, due_at, done) VALUES (?,?,?,0)", (rid, text, due_at))
    _db().commit()
    return {"id": rid, "text": text, "dueAt": due_at, "done": False}


def list_reminders() -> List[Dict]:
    rows = _db().execute("SELECT id, text, due_at, done FROM reminders ORDER BY due_at ASC").fetchall()
    return [{"id": r[0], "text": r[1], "dueAt": r[2], "done": bool(r[3])} for r in rows]


def toggle_reminder(rid: str) -> None:
    _db().execute("UPDATE reminders SET done = 1 - done WHERE id = ?", (rid,))
    _db().commit()
