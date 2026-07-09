"""Text-to-speech with three tiers: ElevenLabs (best quality, needs an API key and
internet), Microsoft Edge's free neural voices (no key, needs internet), and pyttsx3
(fully offline, uses whatever voice your OS ships). `settings["ttsProvider"]` picks the
tier: "auto" (try ElevenLabs if a key is configured, then Edge, then offline), or force
one of "elevenlabs" | "edge" | "offline" directly. Playback runs in a background thread
so speak() never blocks the caller, and stop_speaking() interrupts mid-sentence the
moment the user starts talking again.
"""

import os
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

import requests

import config
from core.logger import get_logger

logger = get_logger("tts")

DEFAULT_EDGE_VOICE = "en-GB-RyanNeural"  # calm, measured British male neural voice

# ElevenLabs' "George" premade voice — warm, resonant British male, from their own
# quickstart docs. Verify it still sounds right in Settings once you add a key; ElevenLabs'
# voice library can change, and this ID isn't something that could be tested from here.
DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"

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


def list_elevenlabs_voices() -> List[Dict[str, str]]:
    api_key = config.get_api_key("elevenlabs")
    if not api_key:
        raise RuntimeError("Add an ElevenLabs API key in Settings first.")
    res = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": api_key}, timeout=10)
    res.raise_for_status()
    voices = res.json().get("voices", [])
    return [
        {
            "id": v["voice_id"],
            "name": v.get("name", v["voice_id"]),
            "accent": (v.get("labels") or {}).get("accent", ""),
        }
        for v in voices
    ]


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


def _provider_chain(settings: Dict[str, Any]) -> List[str]:
    preference = settings.get("ttsProvider", "auto")
    if preference == "elevenlabs":
        return ["elevenlabs", "offline"]
    if preference == "edge":
        return ["edge", "offline"]
    if preference == "offline":
        return ["offline"]
    # auto
    chain = []
    if config.get_api_key("elevenlabs"):
        chain.append("elevenlabs")
    chain.append("edge")
    chain.append("offline")
    return chain


def _speak_blocking(text: str, settings: Dict[str, Any]) -> None:
    with _play_lock:
        _should_stop.clear()
        rate = settings.get("speechRate", 1.05)

        for provider in _provider_chain(settings):
            try:
                if provider == "elevenlabs":
                    voice_id = settings.get("elevenLabsVoiceId") or DEFAULT_ELEVENLABS_VOICE_ID
                    _speak_elevenlabs(text, voice_id)
                elif provider == "edge":
                    _speak_edge(text, settings.get("voiceName") or DEFAULT_EDGE_VOICE, rate)
                else:
                    _speak_offline(text, rate)
                return
            except Exception as err:  # noqa: BLE001
                logger.warning("TTS provider %s failed (%s), trying next", provider, err)
        logger.error("All TTS providers failed for: %s", text[:80])


def _speak_elevenlabs(text: str, voice_id: str) -> None:
    api_key = config.get_api_key("elevenlabs")
    if not api_key:
        raise RuntimeError("No ElevenLabs API key configured")

    res = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=30,
    )
    if not res.ok:
        raise RuntimeError(f"ElevenLabs TTS failed ({res.status_code}): {res.text[:200]}")

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(res.content)
        _play_file(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


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
    # Try pygame/SDL first; if its audio backend isn't available (common in a Chromebook
    # Linux container, where SDL can't find an output device), fall back to a command-line
    # player. This makes voice output work on far more setups than pygame alone.
    try:
        import pygame

        _ensure_mixer()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if _should_stop.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.05)
        return
    except Exception as err:  # noqa: BLE001
        logger.info("pygame audio unavailable (%s), trying a command-line player instead.", err)

    _play_file_cli(path)


def _play_file_cli(path: str) -> None:
    """Plays an mp3 via whichever common CLI player is installed. On Debian/Crostini,
    `sudo apt install mpg123` or `ffmpeg` provides one; see README for the one-liner."""
    import shutil
    import subprocess

    players = [
        ["mpg123", "-q", path],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
        ["cvlc", "--play-and-exit", "--intf", "dummy", path],
        ["paplay", path],
    ]
    for cmd in players:
        if shutil.which(cmd[0]):
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                while proc.poll() is None:
                    if _should_stop.is_set():
                        proc.terminate()
                        break
                    time.sleep(0.05)
                return
            except Exception as err:  # noqa: BLE001
                logger.info("Player %s failed: %s", cmd[0], err)
                continue
    logger.warning(
        "No working audio player found. Install one with:  sudo apt install -y mpg123  (Debian/Crostini)."
    )


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
