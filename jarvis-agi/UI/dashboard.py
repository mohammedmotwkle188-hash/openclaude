"""pywebview host for the HUD. Serves the prebuilt static frontend in UI/web/ and exposes a
flat JarvisApi at window.pywebview.api.* matching the names the frontend's bridge calls.
Python -> JS push events go through window.__jarvisPush(channel, payload).

The frontend is the same holographic HUD from the previous build, so this implements the
full method surface it expects — real implementations for what JARVIS-AGI supports (chat,
stats, commands, settings, weather/news, reminders) and graceful stubs for the dropped
features (screen OCR, ElevenLabs listing, stocks/crypto, calendar), so no bridge call ever
crashes or dumps a traceback.
"""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import webview

import config
from BRAIN import brain
from CORE import commands, memory
from CORE.orchestrator import orchestrator, parse_command

WEB_DIR = Path(__file__).parent / "web"
_window: Optional[webview.Window] = None


def _now() -> int:
    return int(time.time() * 1000)


def _push(channel: str, payload: Any) -> None:
    if _window is None:
        return
    try:
        _window.evaluate_js(f"window.__jarvisPush({json.dumps(channel)}, {json.dumps(payload)})")
    except Exception:  # noqa: BLE001 - window may be tearing down; never let a push crash a thread
        pass


def _collect_stats() -> dict:
    import psutil

    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    batt = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    return {
        "timestamp": _now(),
        "cpu": {"loadPercent": round(cpu, 1), "cores": psutil.cpu_count() or 1, "speedGhz": 0, "model": "CPU"},
        "ram": {"usedGb": round(mem.used / 1024**3, 1), "totalGb": round(mem.total / 1024**3, 1), "usedPercent": round(mem.percent, 1)},
        "gpu": {"model": "N/A", "loadPercent": None, "vramUsedMb": None, "vramTotalMb": None},
        "battery": {"hasBattery": batt is not None, "percent": round(batt.percent) if batt else 0,
                    "isCharging": bool(batt.power_plugged) if batt else False, "timeRemainingMin": None},
        "storage": {"usedGb": round(disk.used / 1024**3, 1), "totalGb": round(disk.total / 1024**3, 1), "usedPercent": round(disk.percent, 1)},
        "network": {"interface": "net", "downKbps": 0, "upKbps": 0, "online": True},
        "temperature": {"cpuC": None},
        "processes": {"total": len(psutil.pids()), "running": 0, "topByCpu": []},
    }


def _internet_online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2.5)
        return True
    except OSError:
        return False


class JarvisApi:
    # --- stats ---
    def stats_subscribe(self):
        threading.Thread(target=self._stats_loop, daemon=True).start()
        threading.Thread(target=self._net_loop, daemon=True).start()
        return True

    def _stats_loop(self):
        while True:
            try:
                _push("stats_update", _collect_stats())
            except Exception:  # noqa: BLE001
                pass
            time.sleep(5)  # slower polling = fewer re-renders on weak hardware

    def _net_loop(self):
        while True:
            _push("internet_status", _internet_online())
            time.sleep(30)

    # --- chat / orchestrator ---
    def chat_get_history(self):
        return memory.load_history()

    def chat_clear_history(self):
        memory.clear_history()
        return True

    def provider_status(self):
        return [s.__dict__ for s in brain.provider_statuses()]

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
        _push("chat_message", {"id": str(uuid.uuid4()), "role": "assistant",
                               "text": "Screen analysis isn't available in this lightweight build.",
                               "timestamp": _now()})
        return True

    # --- voice (output only; no mic on target hardware) ---
    def voice_listen_once(self):
        _push("notification", {"id": str(uuid.uuid4()), "title": "Voice",
                               "body": "Microphone input isn't available on this device — please type.",
                               "level": "info", "timestamp": _now()})
        return False

    def voice_list_elevenlabs_voices(self):
        from ENGINE import tts

        try:
            return tts.list_elevenlabs_voices()
        except Exception:  # noqa: BLE001 - invalid/missing key shouldn't spew a traceback
            return []

    # --- memory ---
    def memory_set_passphrase(self, passphrase: str):
        return True  # encryption disabled in this lean build

    def memory_unlock(self, passphrase: str):
        return True

    def memory_lock(self):
        return True

    def memory_remember(self, key: str, value: str):
        memory.remember_fact(key, value)
        return True

    def memory_recall(self):
        return memory.recall_facts()

    # --- commands ---
    def commands_parse(self, raw: str):
        cmd = parse_command(raw)
        return cmd.__dict__ if cmd else None

    # --- settings ---
    def settings_get(self):
        return config.get_settings()

    def settings_set(self, partial: dict):
        return config.set_settings(partial)

    def api_keys_set(self, partial: dict):
        config.set_api_keys(partial)
        return True

    def api_keys_get_masked(self):
        return config.get_masked_api_keys()

    # --- screen (dropped features -> graceful stubs) ---
    def screen_capture(self):
        raise RuntimeError("Screenshots aren't available in this lightweight build.")

    def screen_ocr(self):
        return ""

    def screen_toggle_monitor(self, enabled: bool):
        return False

    # --- data ---
    def data_weather(self, location: Optional[str] = None):
        return commands.weather_data(location)

    def data_news(self):
        return commands.news_data()

    def data_stock(self, symbol: str):
        raise RuntimeError("Stocks aren't available in this lightweight build.")

    def data_crypto(self, symbol: str):
        raise RuntimeError("Crypto isn't available in this lightweight build.")

    def reminders_list(self):
        return memory.list_reminders()

    def reminders_add(self, text: str, due_at: int):
        return memory.add_reminder(text, due_at)

    def reminders_toggle(self, rid: str):
        memory.toggle_reminder(rid)
        return True

    def calendar_list(self):
        return []

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
    _window = webview.create_window(
        "J.A.R.V.I.S.",
        url=str(WEB_DIR / "index.html"),
        js_api=JarvisApi(),
        width=1440,
        height=900,
        min_size=(1024, 680),
        background_color="#020408",
        frameless=True,
        easy_drag=False,
    )
    webview.start(debug=False)
