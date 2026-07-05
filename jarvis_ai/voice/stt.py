"""Push-to-talk speech-to-text — a single blocking listen-and-transcribe call.

Uses SpeechRecognition's default Google Web Speech backend (free, no API key, needs
internet). Swap in `openai-whisper` / `faster-whisper` here for a fully offline engine.
"""

from typing import Optional

import speech_recognition as sr


def listen_once(timeout: float = 8.0, phrase_time_limit: float = 15.0) -> Optional[str]:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as err:
        raise RuntimeError(f"Speech recognition service error: {err}") from err
