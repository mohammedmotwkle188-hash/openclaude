"""File operations sandboxed to the user's home directory — see utils.helpers.resolve_in_home."""

import shutil
import subprocess
import sys

from utils.helpers import resolve_in_home


def create_file(target: str, content: str = "") -> str:
    resolved = resolve_in_home(target)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Created {resolved}"


def delete_file(target: str) -> str:
    resolved = resolve_in_home(target)
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()
    return f"Deleted {resolved}"


def move_file(src: str, dst: str) -> str:
    source = resolve_in_home(src)
    dest = resolve_in_home(dst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return f"Moved {source} -> {dest}"


def rename_file(target: str, new_name: str) -> str:
    source = resolve_in_home(target)
    dest = source.parent / new_name
    source.rename(dest)
    return f"Renamed to {new_name}"


def open_folder(target: str) -> str:
    resolved = resolve_in_home(target)
    if sys.platform == "win32":
        import os

        os.startfile(resolved)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(resolved)], check=False)
    else:
        subprocess.run(["xdg-open", str(resolved)], check=False)
    return f"Opened {resolved}"
