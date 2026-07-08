"""Local settings + API keys for JARVIS-AGI.

Plain JSON at ~/.jarvis_agi/config.json (permissioned 0600). Groq is the default brain,
so the only key you actually need is a free Groq key. Everything else is optional.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(os.path.expanduser("~")) / ".jarvis_agi"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "dark",
    "animationsEnabled": True,
    "wakeWordEnabled": False,  # no microphone on the target hardware; type instead
    "voiceEnabled": True,
    "voiceName": None,             # edge-tts voice; None -> DEFAULT_EDGE_VOICE
    "elevenLabsVoiceId": None,     # kept for HUD compatibility; ElevenLabs is optional
    "ttsProvider": "edge",         # "edge" (free British voice) is the reliable default
    "speechRate": 1.05,
    "providerOrder": ["groq", "openrouter", "gemini"],  # Groq first — only key you need
    "groqModel": "llama-3.3-70b-versatile",
    "openRouterModel": "meta-llama/llama-3.3-70b-instruct:free",
    "geminiModel": "gemini-2.0-flash",
    "ollamaBaseUrl": "http://127.0.0.1:11434",  # unused by default; kept for HUD compat
    "weatherLocation": "London,UK",
    "hasPassphrase": False,
}

API_KEY_FIELDS = ["groq", "openrouter", "gemini", "elevenlabs", "openweather", "newsapi"]

_cache: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    APP_DIR.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
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
        pass


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
