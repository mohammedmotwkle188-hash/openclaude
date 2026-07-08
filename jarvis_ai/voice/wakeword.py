"""Continuous "Jarvis" wake-word listening — same two-phase logic as the Electron build's
voiceEngine.ts (say "Jarvis" + a command in one breath, or "Jarvis" then pause and wait),
just driven by repeated short SpeechRecognition listens instead of the browser's
continuous recognition API. No dedicated wake-word model (Porcupine/openWakeWord) is
wired in — this rescans full short phrases for the word "jarvis", which is simpler to
run with no extra model download but less efficient than a real wake-word engine.
"""

from __future__ import annotations

import re
import threading
from typing import Callable, Optional

import speech_recognition as sr

from core.logger import get_logger

logger = get_logger("wakeword")

WAKE_WORD = re.compile(r"\bjarvis\b", re.IGNORECASE)


class WakeWordListener:
    def __init__(
        self,
        on_command: Callable[[str], None],
        on_wake_triggered: Optional[Callable[[], None]] = None,
        on_listening_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.on_command = on_command
        self.on_wake_triggered = on_wake_triggered or (lambda: None)
        self.on_listening_change = on_listening_change or (lambda _v: None)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active_mode = False

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._stop.clear()
        self._active_mode = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        recognizer = sr.Recognizer()
        try:
            mic = sr.Microphone()
        except Exception as err:  # noqa: BLE001 - PyAudio missing raises AttributeError, no-mic raises OSError
            # No working microphone (very common on Chromebooks / headless Linux, where PyAudio
            # isn't installed). Wake-word listening just isn't available; the user types instead.
            # Log a single clean line rather than letting the thread die with a scary traceback.
            logger.info("Wake-word listening unavailable (no microphone/PyAudio). Type commands instead.")
            return

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

        while not self._stop.is_set():
            try:
                self.on_listening_change(True)
                with mic as source:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                continue
            finally:
                self.on_listening_change(False)

            try:
                text = recognizer.recognize_google(audio)
            except (sr.UnknownValueError, sr.RequestError):
                continue

            self._handle_transcript(text)

    def _handle_transcript(self, text: str) -> None:
        if not self._active_mode:
            if WAKE_WORD.search(text):
                self.on_wake_triggered()
                remainder = WAKE_WORD.sub("", text).strip()
                if len(remainder) > 2:
                    self.on_command(remainder)
                else:
                    self._active_mode = True
        else:
            self._active_mode = False
            self.on_command(text)
