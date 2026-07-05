"""Screen text extraction via Tesseract OCR (requires the system `tesseract` binary —
see README) plus a live monitor loop that periodically OCRs the screen and reports
back through a push callback, mirroring the Electron build's screen monitor feature.
"""

import threading
import time
from typing import Callable, Optional

import pyautogui
import pytesseract

from utils.helpers import new_id, now_ms

_monitor_thread: Optional[threading.Thread] = None
_monitor_stop = threading.Event()


def screenshot_text() -> str:
    img = pyautogui.screenshot()
    return pytesseract.image_to_string(img).strip()


def toggle_monitor(enabled: bool, push_event: Callable[[str, dict], None]) -> bool:
    global _monitor_thread
    _monitor_stop.set()
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=1)
    _monitor_stop.clear()

    if enabled:
        def loop():
            while not _monitor_stop.wait(15):
                try:
                    text = screenshot_text()
                except Exception:  # noqa: BLE001
                    continue
                push_event("notification", {
                    "id": new_id(),
                    "title": "Screen scan",
                    "body": (text[:240] or "(no legible text detected)"),
                    "level": "info",
                    "timestamp": now_ms(),
                })

        _monitor_thread = threading.Thread(target=loop, daemon=True)
        _monitor_thread.start()
    return enabled
