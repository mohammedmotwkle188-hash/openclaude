"""Text-to-speech: Microsoft Edge's neural voices (free, no key, needs internet) with a
calm British male voice by default, falling back to the offline OS voice via pyttsx3 if
edge-tts fails. Playback runs in a background thread so speak() never blocks the caller,
and stop_speaking() interrupts mid-sentence the moment the user starts talking again.
"""

import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional

from core.logger import get_logger

logger = get_logger("tts")

DEFAULT_VOICE = "en-GB-RyanNeural"  # calm, measured British male neural voice

_play_lock = threading.Lock()
_should_stop = threading.Event()
_mixer_ready = False


def _ensure_mixer() -> None:
    global _mixer_ready
    if _mixer_ready:
        return
    import pygame

    pygame.mixer.init()
    _mixer_ready = True


def speak(text: str, settings: Optional[Dict[str, Any]] = None) -> None:
    if not text.strip():
        return
    settings = settings or {}
    threading.Thread(target=_speak_blocking, args=(text, settings), daemon=True).start()


def stop_speaking() -> None:
    _should_stop.set()
    try:
        import pygame

        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
    except Exception:  # noqa: BLE001
        pass


def _speak_blocking(text: str, settings: Dict[str, Any]) -> None:
    with _play_lock:
        _should_stop.clear()
        voice = settings.get("voiceName") or DEFAULT_VOICE
        rate = settings.get("speechRate", 1.05)
        try:
            _speak_edge(text, voice, rate)
        except Exception as err:  # noqa: BLE001
            logger.warning("edge-tts failed (%s), falling back to offline voice", err)
            _speak_offline(text, rate)


def _speak_edge(text: str, voice: str, rate: float) -> None:
    import asyncio

    import edge_tts

    percent = round((rate - 1.0) * 100)
    rate_str = f"{'+' if percent >= 0 else ''}{percent}%"

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    async def synth() -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate_str)
        await communicate.save(path)

    try:
        asyncio.run(synth())
        _play_file(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _play_file(path: str) -> None:
    import pygame

    _ensure_mixer()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if _should_stop.is_set():
            pygame.mixer.music.stop()
            break
        time.sleep(0.05)


def _speak_offline(text: str, rate: float) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", int(180 * rate))
    for voice in engine.getProperty("voices"):
        name = (voice.name or "").lower()
        vid = (voice.id or "").lower()
        if "en-gb" in vid or "british" in name or "uk" in name:
            engine.setProperty("voice", voice.id)
            break
    engine.say(text)
    engine.runAndWait()
