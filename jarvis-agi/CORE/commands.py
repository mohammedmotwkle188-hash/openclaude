"""Lightweight, reliable commands — the ones that actually work on a Chromebook/Linux.

No webcam, OCR, mouse/keyboard automation, or heavy integrations (those bloated the old
build and don't work on this hardware). Each command returns a short spoken-friendly
string. Weather/news need optional keys; everything else is keyless.
"""

from __future__ import annotations

import datetime as dt
import platform
import shutil
import subprocess
import urllib.parse
import webbrowser
from typing import Optional

import config

PLATFORM = platform.system()  # "Linux" | "Darwin" | "Windows"

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
