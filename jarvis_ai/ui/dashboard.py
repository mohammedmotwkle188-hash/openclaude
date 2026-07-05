"""pywebview host for the HUD: serves the pre-built static frontend in ui/web/ and exposes
a flat JarvisApi surface at window.pywebview.api.* (see src/lib/bridge.ts on the frontend
side for the matching call names). Python -> JS push events go through window.evaluate_js.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

import webview

import config
from core.logger import get_logger
from core.orchestrator import orchestrator, parse_command
from memory import long_term
from tools import automation, system_control
from utils.helpers import new_id, now_ms
from vision import ocr
from voice import stt
from voice.wakeword import WakeWordListener

logger = get_logger("dashboard")

WEB_DIR = Path(__file__).parent / "web"

_window: Optional[webview.Window] = None
_wake_listener: Optional[WakeWordListener] = None


def _push(channel: str, payload: Any) -> None:
    if _window is None:
        return
    try:
        _window.evaluate_js(f"window.__jarvisPush({json.dumps(channel)}, {json.dumps(payload)})")
    except Exception:  # noqa: BLE001 - the window may be mid-teardown; never let a push crash a background thread
        pass


def _ensure_wake_listener() -> WakeWordListener:
    global _wake_listener
    if _wake_listener is None:
        _wake_listener = WakeWordListener(
            on_command=orchestrator.handle_text,
            on_wake_triggered=lambda: _push("voice_wake_triggered", {}),
            on_listening_change=lambda v: _push("voice_listening_change", v),
        )
    return _wake_listener


class JarvisApi:
    # --- stats ---
    def stats_subscribe(self) -> bool:
        threading.Thread(target=self._stats_loop, daemon=True).start()
        threading.Thread(target=self._net_loop, daemon=True).start()
        return True

    def _stats_loop(self) -> None:
        while True:
            try:
                _push("stats_update", system_control.collect_stats())
            except Exception:  # noqa: BLE001
                logger.exception("Stats collection failed")
            time.sleep(2)

    def _net_loop(self) -> None:
        while True:
            _push("internet_status", system_control.check_internet_online())
            time.sleep(10)

    # --- chat / orchestrator ---
    def chat_get_history(self):
        return long_term.load_history()

    def chat_clear_history(self):
        long_term.clear_history()
        return True

    def provider_status(self):
        from core.brain import provider_statuses

        return [s.__dict__ for s in provider_statuses()]

    def orchestrator_handle_text(self, text: str):
        orchestrator.handle_text(text)
        return True

    def orchestrator_confirm_pending(self):
        orchestrator.confirm_pending()
        return True

    def orchestrator_cancel_pending(self):
        orchestrator.cancel_pending()
        return True

    def orchestrator_interrupt(self):
        orchestrator.interrupt()
        return True

    def orchestrator_analyze_screen(self, question: Optional[str] = None):
        if question:
            orchestrator.analyze_screen(question)
        else:
            orchestrator.analyze_screen()
        return True

    # --- voice ---
    def voice_listen_once(self):
        _push("voice_listening_change", True)
        try:
            text = stt.listen_once()
        finally:
            _push("voice_listening_change", False)
        if text:
            orchestrator.handle_text(text)
        else:
            _push("notification", {
                "id": new_id(), "title": "Voice", "body": "Didn't catch that — try again.",
                "level": "warning", "timestamp": now_ms(),
            })
        return bool(text)

    def voice_list_elevenlabs_voices(self):
        from voice import tts

        return tts.list_elevenlabs_voices()

    # --- memory ---
    def memory_set_passphrase(self, passphrase: str):
        long_term.set_passphrase(passphrase)
        config.set_settings({"hasPassphrase": True})
        return True

    def memory_unlock(self, passphrase: str):
        return long_term.unlock(passphrase)

    def memory_lock(self):
        long_term.lock()
        return True

    def memory_remember(self, key: str, value: str):
        long_term.remember_fact(key, value)
        return True

    def memory_recall(self):
        return long_term.recall_facts()

    # --- commands (parse only; execution happens inside orchestrator_handle_text) ---
    def commands_parse(self, raw: str):
        cmd = parse_command(raw)
        return cmd.__dict__ if cmd else None

    # --- settings ---
    def settings_get(self):
        return config.get_settings()

    def settings_set(self, partial: dict):
        prev_wake = config.get_settings().get("wakeWordEnabled")
        updated = config.set_settings(partial)
        if "wakeWordEnabled" in partial and partial["wakeWordEnabled"] != prev_wake:
            listener = _ensure_wake_listener()
            if partial["wakeWordEnabled"]:
                listener.start()
            else:
                listener.stop()
        return updated

    def api_keys_set(self, partial: dict):
        config.set_api_keys(partial)
        return True

    def api_keys_get_masked(self):
        return config.get_masked_api_keys()

    # --- screen ---
    def screen_capture(self):
        return automation.capture_screenshot()

    def screen_ocr(self):
        return ocr.screenshot_text()

    def screen_toggle_monitor(self, enabled: bool):
        return ocr.toggle_monitor(enabled, _push)

    # --- data ---
    def data_weather(self, location: Optional[str] = None):
        from tools import webdata

        return webdata.fetch_weather(location)

    def data_news(self):
        from tools import webdata

        return webdata.fetch_news()

    def data_stock(self, symbol: str):
        from tools import webdata

        return webdata.fetch_stock_quote(symbol)

    def data_crypto(self, symbol: str):
        from tools import webdata

        return webdata.fetch_crypto_price(symbol)

    def reminders_list(self):
        return long_term.list_reminders()

    def reminders_add(self, text: str, due_at: int):
        return long_term.add_reminder(text, due_at)

    def reminders_toggle(self, reminder_id: str):
        long_term.toggle_reminder(reminder_id)
        return True

    def calendar_list(self):
        return []  # no calendar provider wired up yet — see README

    # --- window ---
    def window_minimize(self):
        if _window:
            try:
                _window.minimize()
            except Exception:  # noqa: BLE001
                pass
        return True

    def window_close(self):
        if _window:
            _window.destroy()
        return True


def run() -> None:
    global _window
    orchestrator.push_event = _push
    api = JarvisApi()
    _window = webview.create_window(
        "J.A.R.V.I.S.",
        url=str(WEB_DIR / "index.html"),
        js_api=api,
        width=1440,
        height=900,
        min_size=(1024, 680),
        background_color="#020408",
        frameless=True,
        easy_drag=False,
    )

    def on_loaded():
        if config.get_settings().get("wakeWordEnabled"):
            _ensure_wake_listener().start()

    _window.events.loaded += on_loaded
    webview.start(debug=False)
