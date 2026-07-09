"""Logging setup plus a tiny pub-sub so the UI's "thoughts" feed can mirror log lines."""

import logging
from logging.handlers import RotatingFileHandler
from typing import Callable, List

from config import APP_DIR

_listeners: List[Callable[[str], None]] = []


class _BroadcastHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        for listener in list(_listeners):
            try:
                listener(message)
            except Exception:
                pass  # a broken UI listener must never take down logging itself


def on_log(callback: Callable[[str], None]) -> Callable[[], None]:
    """Registers a callback invoked with each formatted log line. Returns an unsubscribe fn."""
    _listeners.append(callback)
    return lambda: _listeners.remove(callback) if callback in _listeners else None


def get_logger(name: str = "jarvis") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    APP_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(APP_DIR / "jarvis.log", maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    broadcast = _BroadcastHandler()
    broadcast.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(broadcast)

    return logger
