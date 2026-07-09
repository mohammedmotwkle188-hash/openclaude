"""Quick voice/text notes saved as timestamped text files under ~/.jarvis_ai/notes/."""

import datetime as dt
from pathlib import Path
from typing import List

from config import APP_DIR

NOTES_DIR = APP_DIR / "notes"


def save_note(text: str) -> str:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = NOTES_DIR / f"{stamp}-note.txt"
    path.write_text(text, encoding="utf-8")
    return f"Noted. Saved to {path.name}."


def list_notes(limit: int = 10) -> List[str]:
    if not NOTES_DIR.exists():
        return []
    files = sorted(NOTES_DIR.glob("*-note.txt"), reverse=True)[:limit]
    return [f.read_text("utf-8").strip() for f in files]


def read_latest_note() -> str:
    notes = list_notes(1)
    if not notes:
        return "You don't have any notes yet."
    return f"Your latest note: {notes[0]}"
