"""Persistent memory: SQLite + AES-256-GCM field encryption, gated by a local passphrase.

Python port of the Electron build's electron/services/memory/{db,encryption}.ts. Without
a passphrase set, everything is stored in plaintext locally — same trade-off as before,
made explicit rather than silently "secure by default."
"""

import base64
import os
import sqlite3
import time
from typing import Dict, List, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from config import APP_DIR
from utils.helpers import new_id

DB_FILE = APP_DIR / "jarvis_memory.db"

_conn: Optional[sqlite3.Connection] = None
_key: Optional[bytes] = None


def init_db() -> None:
    global _conn
    APP_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS vault_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            salt TEXT NOT NULL
        )
    """)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            body TEXT NOT NULL,
            provider TEXT,
            timestamp INTEGER NOT NULL
        )
    """)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            key TEXT PRIMARY KEY,
            body TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            due_at INTEGER NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)
    _conn.commit()


def _db() -> sqlite3.Connection:
    if _conn is None:
        init_db()
    return _conn  # type: ignore[return-value]


def _get_or_create_salt() -> bytes:
    row = _db().execute("SELECT salt FROM vault_meta WHERE id = 1").fetchone()
    if row:
        return base64.b64decode(row[0])
    salt = os.urandom(16)
    _db().execute("INSERT INTO vault_meta (id, salt) VALUES (1, ?)", (base64.b64encode(salt).decode(),))
    _db().commit()
    return salt


def has_vault_been_initialized() -> bool:
    return _db().execute("SELECT salt FROM vault_meta WHERE id = 1").fetchone() is not None


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))


def set_passphrase(passphrase: str) -> None:
    global _key
    salt = _get_or_create_salt()
    _key = _derive_key(passphrase, salt)


def unlock(passphrase: str) -> bool:
    global _key
    if not has_vault_been_initialized():
        return False
    salt = _get_or_create_salt()
    _key = _derive_key(passphrase, salt)
    return True


def lock() -> None:
    global _key
    _key = None


def is_unlocked() -> bool:
    return _key is not None


def _encrypt(plaintext: str) -> str:
    if _key is None:
        raise RuntimeError("Vault is locked — set a passphrase in Settings first.")
    nonce = os.urandom(12)
    ct = AESGCM(_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode()


def _decrypt(payload: str) -> str:
    if _key is None:
        raise RuntimeError("Vault is locked — set a passphrase in Settings first.")
    raw = base64.b64decode(payload)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(_key).decrypt(nonce, ct, None).decode("utf-8")


def save_message(role: str, text: str, provider: Optional[str]) -> None:
    body = _encrypt(text) if is_unlocked() else text
    _db().execute(
        "INSERT INTO messages (id, role, body, provider, timestamp) VALUES (?, ?, ?, ?, ?)",
        (new_id(), role, body, provider, int(time.time() * 1000)),
    )
    _db().commit()


def load_history(limit: int = 200) -> List[Dict]:
    rows = _db().execute(
        "SELECT id, role, body, provider, timestamp FROM messages ORDER BY timestamp ASC LIMIT ?", (limit,)
    ).fetchall()
    out = []
    for row_id, role, body, provider, ts in rows:
        if is_unlocked():
            try:
                text = _decrypt(body)
            except Exception:  # noqa: BLE001
                text = "[locked — unlock vault to view]"
        else:
            text = "[locked — set passphrase in Settings to decrypt]"
        out.append({"id": row_id, "role": role, "text": text, "provider": provider, "timestamp": ts})
    return out


def clear_history() -> None:
    _db().execute("DELETE FROM messages")
    _db().commit()


def remember_fact(key: str, value: str) -> None:
    body = _encrypt(value) if is_unlocked() else value
    _db().execute(
        "INSERT INTO memories (key, body, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET body = excluded.body, updated_at = excluded.updated_at",
        (key, body, int(time.time() * 1000)),
    )
    _db().commit()


def recall_facts() -> Dict[str, str]:
    rows = _db().execute("SELECT key, body FROM memories").fetchall()
    out = {}
    for key, body in rows:
        if is_unlocked():
            try:
                out[key] = _decrypt(body)
            except Exception:  # noqa: BLE001
                out[key] = "[locked]"
        else:
            out[key] = "[locked]"
    return out


def add_reminder(text: str, due_at: int) -> Dict:
    reminder_id = new_id()
    _db().execute("INSERT INTO reminders (id, text, due_at, done) VALUES (?, ?, ?, 0)", (reminder_id, text, due_at))
    _db().commit()
    return {"id": reminder_id, "text": text, "dueAt": due_at, "done": False}


def list_reminders() -> List[Dict]:
    rows = _db().execute("SELECT id, text, due_at, done FROM reminders ORDER BY due_at ASC").fetchall()
    return [{"id": r[0], "text": r[1], "dueAt": r[2], "done": bool(r[3])} for r in rows]


def toggle_reminder(reminder_id: str) -> None:
    _db().execute("UPDATE reminders SET done = 1 - done WHERE id = ?", (reminder_id,))
    _db().commit()
