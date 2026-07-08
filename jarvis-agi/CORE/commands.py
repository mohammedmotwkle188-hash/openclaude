"""Lightweight, reliable commands — the ones that actually work on a Chromebook/Linux.

No webcam, OCR, mouse/keyboard automation, or heavy integrations (those bloated the old
build and don't work on this hardware). Each command returns a short spoken-friendly
string. Weather/news need optional keys; everything else is keyless.
"""

from __future__ import annotations

import datetime as dt
import os
import platform
import shutil
import subprocess
import urllib.parse
import webbrowser
import zipfile
from pathlib import Path
from typing import Optional

import config

PLATFORM = platform.system()  # "Linux" | "Darwin" | "Windows"
HOME = Path.home()
REPO_DIR = Path(__file__).resolve().parents[2]  # .../openclaude (parent of jarvis-agi)

APP_URLS = {
    "chrome": "https://google.com",
    "youtube": "https://youtube.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://netflix.com",
    "discord": "https://discord.com/app",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
}


def open_app(name: str) -> str:
    key = name.lower().strip()
    url = APP_URLS.get(key)
    if url:
        webbrowser.open(url)
        return f"Opening {name}."
    if key.startswith("http"):
        webbrowser.open(name)
        return f"Opened {name}."
    # Try launching a real local app on Linux/macOS as a best effort.
    launcher = {"Linux": ["xdg-open"], "Darwin": ["open", "-a"]}.get(PLATFORM)
    if launcher and shutil.which(launcher[0]):
        subprocess.run(launcher + [name], check=False, capture_output=True)
        return f"Trying to open {name}."
    raise RuntimeError(f'I don\'t have "{name}" registered.')


def search_web(engine: str, query: str) -> str:
    q = urllib.parse.quote(query)
    url = (
        f"https://www.youtube.com/results?search_query={q}"
        if engine == "youtube"
        else f"https://www.google.com/search?q={q}"
    )
    webbrowser.open(url)
    return f'Searching {engine} for "{query}".'


def set_volume(percent: int) -> str:
    p = max(0, min(100, percent))
    try:
        if PLATFORM == "Linux":
            if shutil.which("pactl"):
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{p}%"], check=True)
            elif shutil.which("amixer"):
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{p}%"], check=True)
            else:
                raise RuntimeError("no mixer")
        elif PLATFORM == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {p}"], check=True)
        else:
            raise RuntimeError("unsupported")
        return f"Volume set to {p}%."
    except Exception as err:  # noqa: BLE001
        raise RuntimeError("Couldn't change the volume on this system.") from err


def power_action(action: str) -> str:
    cmds = {
        "shutdown": {"Linux": ["systemctl", "poweroff"], "Darwin": ["osascript", "-e", 'tell app "System Events" to shut down']},
        "restart": {"Linux": ["systemctl", "reboot"], "Darwin": ["osascript", "-e", 'tell app "System Events" to restart']},
    }
    cmd = cmds[action].get(PLATFORM)
    if not cmd:
        raise RuntimeError(f"Can't {action} on this platform.")
    subprocess.run(cmd, check=False)
    return f"{'Shutting down' if action == 'shutdown' else 'Restarting'} now."


def tell_time() -> str:
    return f"It's {dt.datetime.now().strftime('%H:%M')}."


def tell_date() -> str:
    return f"Today is {dt.datetime.now().strftime('%A, %d %B %Y')}."


def tell_joke() -> str:
    import random

    import requests

    try:
        res = requests.get(
            "https://icanhazdadjoke.com/", headers={"Accept": "application/json", "User-Agent": "JarvisAGI"}, timeout=6
        )
        if res.ok and res.json().get("joke"):
            return res.json()["joke"]
    except requests.RequestException:
        pass
    return random.choice([
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "I would tell you a UDP joke, but you might not get it.",
        "There are 10 kinds of people: those who understand binary, and those who don't.",
    ])


def weather_data(location: Optional[str] = None) -> dict:
    """Structured weather for the HUD widget. Raises with a friendly message if no key."""
    import requests

    key = config.get_api_key("openweather")
    if not key:
        raise RuntimeError("Add an OpenWeather key in Settings for live weather.")
    loc = (location or "").strip() or config.get_settings()["weatherLocation"]
    res = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": loc, "units": "metric", "appid": key}, timeout=10,
    )
    if not res.ok:
        raise RuntimeError(f'Weather lookup failed for "{loc}".')
    d = res.json()
    return {
        "location": d.get("name", loc),
        "tempC": round(d["main"]["temp"]),
        "condition": d["weather"][0]["description"],
        "humidityPercent": d["main"]["humidity"],
    }


def news_data() -> list:
    """Structured headlines for the HUD widget. Raises with a friendly message if no key."""
    import requests

    key = config.get_api_key("newsapi")
    if not key:
        raise RuntimeError("Add a NewsAPI key in Settings for headlines.")
    res = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"language": "en", "pageSize": 6, "apiKey": key}, timeout=10,
    )
    if not res.ok:
        raise RuntimeError("News lookup failed.")
    return [
        {"id": str(i), "title": a["title"], "source": (a.get("source") or {}).get("name", ""), "url": a.get("url", "#")}
        for i, a in enumerate(res.json().get("articles", []))
    ]


# --------------------------------------------------------------------------------------
# Chromebook-safe feature pack: files, PDF, media, backups, self-update.
# All pure-Python + keyless. Anything touching the filesystem stays inside $HOME.
# --------------------------------------------------------------------------------------

# Friendly folder aliases -> real paths under the user's home directory.
_FOLDER_ALIASES = {
    "home": HOME,
    "downloads": HOME / "Downloads",
    "download": HOME / "Downloads",
    "documents": HOME / "Documents",
    "docs": HOME / "Documents",
    "desktop": HOME / "Desktop",
    "pictures": HOME / "Pictures",
    "photos": HOME / "Pictures",
    "music": HOME / "Music",
    "videos": HOME / "Videos",
}


def _resolve_in_home(candidate: Path) -> Path:
    """Resolve a path and guarantee it stays inside $HOME (blocks ../ traversal)."""
    resolved = candidate.expanduser().resolve()
    home = HOME.resolve()
    if resolved != home and home not in resolved.parents:
        raise RuntimeError("For safety, Jarvis only touches files inside your home folder.")
    return resolved


def _resolve_folder(folder: Optional[str]) -> Path:
    name = (folder or "home").lower().strip()
    base = _FOLDER_ALIASES.get(name, HOME / (folder or ""))
    return _resolve_in_home(base)


def list_files(folder: Optional[str] = None, limit: int = 25) -> str:
    """List files in a home-scoped folder (e.g. 'downloads')."""
    path = _resolve_folder(folder)
    if not path.exists():
        return f"I couldn't find a folder called {folder or 'home'}."
    if not path.is_dir():
        return f"{path.name} is a file, not a folder."
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir() if not p.name.startswith("."))
    if not entries:
        return f"{path.name} is empty."
    shown = entries[:limit]
    more = f" (and {len(entries) - limit} more)" if len(entries) > limit else ""
    return f"{path.name} has {len(entries)} items: " + ", ".join(shown) + more + "."


def _find_in_home(name: str) -> Optional[Path]:
    """Find a file by name in the common home folders (exact, then case-insensitive)."""
    name = name.strip()
    direct = _resolve_in_home(HOME / name)
    if direct.exists():
        return direct
    search_roots = [HOME, HOME / "Downloads", HOME / "Documents", HOME / "Desktop"]
    lower = name.lower()
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.iterdir():
            if p.name.lower() == lower:
                return p
    return None


def open_file(name: str) -> str:
    """Open a file from the home folders with the system default app."""
    target = _find_in_home(name)
    if target is None:
        return f'I couldn\'t find a file called "{name}" in your home folders.'
    opener = {"Linux": "xdg-open", "Darwin": "open"}.get(PLATFORM)
    if opener and shutil.which(opener):
        subprocess.run([opener, str(target)], check=False, capture_output=True)
        return f"Opening {target.name}."
    webbrowser.open(target.as_uri())
    return f"Opening {target.name}."


def read_pdf(name: str) -> str:
    """Extract text from a home-folder PDF. Returns text for the brain to summarise.
    pypdf is imported lazily so a missing wheel never breaks the app."""
    target = _find_in_home(name if name.lower().endswith(".pdf") else f"{name}.pdf")
    if target is None:
        return f'I couldn\'t find a PDF called "{name}" in your home folders.'
    try:
        from pypdf import PdfReader
    except ImportError:
        return ("PDF reading needs one small library. In the terminal run:\n"
                "  source .venv/bin/activate && pip install pypdf\nthen ask me again.")
    try:
        reader = PdfReader(str(target))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as err:  # noqa: BLE001
        return f"I couldn't read {target.name} ({err})."
    text = text.strip()
    if not text:
        return f"{target.name} has no extractable text (it may be a scanned image)."
    return text[:6000]  # cap so the summary prompt stays small


def play(query: str, service: str = "youtube") -> str:
    """Open a song/video search on YouTube (default) or Spotify."""
    q = urllib.parse.quote(query)
    if service == "spotify":
        webbrowser.open(f"https://open.spotify.com/search/{q}")
        return f'Opening Spotify for "{query}".'
    webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
    return f'Playing "{query}" on YouTube.'


def backup() -> str:
    """Zip the whole ~/.jarvis_agi folder (config + memory db) into ~/jarvis-backups."""
    src = config.APP_DIR
    if not src.exists():
        return "There's nothing to back up yet."
    dest_dir = HOME / "jarvis-backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    archive = dest_dir / f"jarvis-{stamp}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(src.parent))
    return f"Backed up your data to {archive}."


def self_update() -> str:
    """Run `git pull` in the project repo and report the result."""
    if not shutil.which("git"):
        return "Git isn't installed, so I can't update myself."
    try:
        res = subprocess.run(
            ["git", "-C", str(REPO_DIR), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as err:  # noqa: BLE001
        return f"Update failed: {err}"
    out = (res.stdout + res.stderr).strip()
    if res.returncode != 0:
        return f"Update didn't go through: {out.splitlines()[-1] if out else 'unknown error'}"
    if "Already up to date" in out:
        return "I'm already on the latest version."
    return "Updated to the latest version. Restart me to load the changes."
