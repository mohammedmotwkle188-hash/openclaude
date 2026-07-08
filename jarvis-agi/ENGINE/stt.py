"""Speech-to-text + "Jarvis" wake word (best-effort on Chromebook/Crostini).

Uses the SpeechRecognition library with Google's free Web Speech backend (needs internet)
against the system microphone. On ChromeOS this only works if you enable Linux mic access
(Settings -> Developers -> Linux -> microphone) AND install PyAudio (see README). It is
deliberately fault-tolerant: if there's no mic/PyAudio, it logs one clean line and stays
quiet rather than crashing — you can still type.
"""

from __future__ import annotations

import re
import threading
from typing import Callable, Optional

WAKE_WORD = re.compile(r"\bjarvis\b", re.IGNORECASE)


def _log(msg: str) -> None:
    print(f"[stt] {msg}", flush=True)


def _make_recognizer():
    import speech_recognition as sr

    return sr, sr.Recognizer()


def listen_once(timeout: float = 8.0, phrase_limit: float = 12.0) -> Optional[str]:
    """Capture and transcribe a single phrase (used by the mic button)."""
    try:
        sr, recognizer = _make_recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
        try:
            return recognizer.recognize_google(audio)
        except (sr.UnknownValueError, sr.RequestError):
            return None
    except Exception as err:  # noqa: BLE001 - missing mic/PyAudio, etc.
        _log(f"Mic unavailable ({err}). Type instead, or see README to enable Chromebook mic.")
        return None


def mic_available() -> bool:
    try:
        import speech_recognition as sr

        sr.Microphone()  # raises if PyAudio missing or no input device
        return True
    except Exception:  # noqa: BLE001
        return False


class WakeWordListener:
    """Continuously listens; when it hears 'Jarvis', it triggers (and treats anything said
    after the word in the same breath as the command)."""

    def __init__(
        self,
        on_command: Callable[[str], None],
        on_wake: Callable[[], None],
        on_listening: Callable[[bool], None],
    ) -> None:
        self.on_command = on_command
        self.on_wake = on_wake
        self.on_listening = on_listening
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active = False

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running():
            return
        self._stop.clear()
        self._active = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            mic = sr.Microphone()
        except Exception as err:  # noqa: BLE001
            _log(f"Wake word off — no working microphone ({err}). Enable Chromebook Linux mic + install PyAudio.")
            return

        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

        while not self._stop.is_set():
            try:
                self.on_listening(True)
                with mic as source:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            except Exception:  # noqa: BLE001 - timeout / transient mic hiccup
                continue
            finally:
                self.on_listening(False)

            try:
                text = recognizer.recognize_google(audio)
            except Exception:  # noqa: BLE001
                continue

            self._handle(text)

    def _handle(self, text: str) -> None:
        if not self._active:
            if WAKE_WORD.search(text):
                self.on_wake()
                rest = WAKE_WORD.sub("", text).strip()
                if len(rest) > 2:
                    self.on_command(rest)
                else:
                    self._active = True  # said just "Jarvis" -> wait for the next phrase
        else:
            self._active = False
            self.on_command(text)
