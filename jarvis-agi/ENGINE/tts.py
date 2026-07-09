"""Text-to-speech: free British voice via Microsoft Edge's neural voices (edge-tts, no key),
played through a command-line player. On ChromeOS/Crostini, pygame/SDL usually can't find an
audio device, so we shell out to `mpg123` (or ffplay/paplay) instead — that's the reliable
path. Voice is output-only; there's no microphone dependency here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Dict, Optional

import config

DEFAULT_EDGE_VOICE = "en-GB-RyanNeural"  # calm British male
# ElevenLabs "George" (British male) — used only if the user sets an ElevenLabs key.
DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

_play_lock = threading.Lock()
_should_stop = threading.Event()
_current_proc: Optional[subprocess.Popen] = None


def _log(msg: str) -> None:
    print(f"[tts] {msg}", flush=True)


def speak(text: str, settings: Optional[Dict[str, Any]] = None) -> None:
    if not text.strip():
        return
    settings = settings or config.get_settings()
    threading.Thread(target=_speak_blocking, args=(text, settings), daemon=True).start()


def stop_speaking() -> None:
    _should_stop.set()
    global _current_proc
    if _current_proc and _current_proc.poll() is None:
        try:
            _current_proc.terminate()
        except Exception:  # noqa: BLE001
            pass


def _provider_chain(settings: Dict[str, Any]):
    pref = settings.get("ttsProvider", "edge")
    if pref == "elevenlabs":
        return ["elevenlabs", "edge", "offline"]
    if pref == "offline":
        return ["offline"]
    if pref == "auto":
        chain = []
        if config.get_api_key("elevenlabs"):
            chain.append("elevenlabs")
        return chain + ["edge", "offline"]
    return ["edge", "offline"]  # default


def _speak_blocking(text: str, settings: Dict[str, Any]) -> None:
    with _play_lock:
        _should_stop.clear()
        rate = settings.get("speechRate", 1.05)
        for provider in _provider_chain(settings):
            try:
                if provider == "elevenlabs":
                    _speak_elevenlabs(text, settings.get("elevenLabsVoiceId") or DEFAULT_ELEVENLABS_VOICE_ID)
                elif provider == "edge":
                    _speak_edge(text, settings.get("voiceName") or DEFAULT_EDGE_VOICE, rate)
                else:
                    _speak_offline(text, rate)
                return
            except Exception as err:  # noqa: BLE001
                _log(f"{provider} TTS failed ({err}); trying next.")
        _log("All TTS engines failed.")


def _speak_edge(text: str, voice: str, rate: float) -> None:
    import asyncio

    import edge_tts

    percent = round((rate - 1.0) * 100)
    rate_str = f"{'+' if percent >= 0 else ''}{percent}%"
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    async def synth() -> None:
        await edge_tts.Communicate(text, voice, rate=rate_str).save(path)

    try:
        asyncio.run(synth())
        _play_file(path)
    finally:
        _safe_remove(path)


def _speak_elevenlabs(text: str, voice_id: str) -> None:
    import requests

    api_key = config.get_api_key("elevenlabs")
    if not api_key:
        raise RuntimeError("No ElevenLabs key")
    res = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Accept": "audio/mpeg", "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=30,
    )
    if not res.ok:
        raise RuntimeError(f"ElevenLabs {res.status_code}")
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(res.content)
        _play_file(path)
    finally:
        _safe_remove(path)


def _speak_offline(text: str, rate: float) -> None:
    # Last resort: espeak/espeak-ng if present (tiny, offline, robotic but always works).
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak:
        raise RuntimeError("no offline TTS (install espeak-ng)")
    words_per_min = int(160 * rate)
    subprocess.run([espeak, "-v", "en-gb", "-s", str(words_per_min), text],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def _play_file(path: str) -> None:
    """Play an mp3 via whichever CLI player is installed. Interruptible via stop_speaking()."""
    global _current_proc
    players = [
        ["mpg123", "-q", path],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
        ["cvlc", "--play-and-exit", "--intf", "dummy", path],
        ["paplay", path],
    ]
    for cmd in players:
        if not shutil.which(cmd[0]):
            continue
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _current_proc = proc
        while proc.poll() is None:
            if _should_stop.is_set():
                proc.terminate()
                break
            time.sleep(0.05)
        _current_proc = None
        return
    raise RuntimeError("no audio player found — install one with: sudo apt install -y mpg123")


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def list_elevenlabs_voices():
    import requests

    api_key = config.get_api_key("elevenlabs")
    if not api_key:
        raise RuntimeError("Add an ElevenLabs API key in Settings first.")
    res = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key}, timeout=10)
    res.raise_for_status()
    return [
        {"id": v["voice_id"], "name": v.get("name", v["voice_id"]), "accent": (v.get("labels") or {}).get("accent", "")}
        for v in res.json().get("voices", [])
    ]
