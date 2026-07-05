"""Local settings + API key persistence.

Plain JSON on disk under the user's home directory, permissioned 0600. This is fine for
non-secret settings, but API keys deserve better than a readable file long-term — wire
this up to the OS credential store (Windows Credential Manager / macOS Keychain /
Secret Service via the `keyring` package) before relying on it for anything sensitive.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(os.path.expanduser("~")) / ".jarvis_ai"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "dark",
    "animationsEnabled": True,
    "wakeWordEnabled": True,
    "voiceEnabled": True,
    "voiceName": None,
    "elevenLabsVoiceId": None,
    "ttsProvider": "auto",  # "auto" | "elevenlabs" | "edge" | "offline" — see voice/tts.py
    "speechRate": 1.05,
    "providerOrder": ["anthropic", "openai", "gemini", "ollama"],
    "ollamaBaseUrl": "http://127.0.0.1:11434",
    "weatherLocation": "London,UK",
    "hasPassphrase": False,
}

API_KEY_FIELDS = ["anthropic", "openai", "gemini", "elevenlabs", "openweather", "newsapi"]

_cache: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    _cache = {
        "settings": {**DEFAULT_SETTINGS, **data.get("settings", {})},
        "apiKeys": {**{k: "" for k in API_KEY_FIELDS}, **data.get("apiKeys", {})},
    }
    return _cache


def _persist() -> None:
    if _cache is None:
        return
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(_cache, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # chmod isn't meaningful on some Windows filesystems; not fatal.


def get_settings() -> Dict[str, Any]:
    return dict(_load()["settings"])


def set_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    store = _load()
    store["settings"].update(partial)
    _persist()
    return dict(store["settings"])


def get_api_key(provider: str) -> Optional[str]:
    return _load()["apiKeys"].get(provider) or None


def set_api_keys(partial: Dict[str, str]) -> None:
    store = _load()
    store["apiKeys"].update({k: v for k, v in partial.items() if v is not None})
    _persist()


def get_masked_api_keys() -> Dict[str, bool]:
    keys = _load()["apiKeys"]
    return {field: bool(keys.get(field)) for field in API_KEY_FIELDS}


def provider_order() -> List[str]:
    return list(get_settings()["providerOrder"])
