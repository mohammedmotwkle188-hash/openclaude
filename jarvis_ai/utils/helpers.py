"""Small shared helpers used across tools/* to keep file access inside the user's home dir."""

import os
import time
import uuid
from pathlib import Path


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id() -> str:
    return str(uuid.uuid4())


def resolve_in_home(target: str) -> Path:
    """Resolves a user-given path and refuses anything outside the home directory.

    File commands are voice/text-driven and only lightly validated by regex, so this is
    the one place that actually enforces the safety boundary before touching disk.
    """
    home = Path(os.path.expanduser("~")).resolve()
    resolved = Path(os.path.expanduser(target)).expanduser()
    resolved = (home / resolved).resolve() if not resolved.is_absolute() else resolved.resolve()
    if home not in resolved.parents and resolved != home:
        raise ValueError("For safety, file operations are restricted to your home directory.")
    return resolved
