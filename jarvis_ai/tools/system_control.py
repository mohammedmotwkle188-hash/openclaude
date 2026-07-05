"""Live system stats + OS-level control: apps, media keys, volume, brightness, power.

Python port of electron/services/system/{stats,commands}.ts using psutil instead of
systeminformation, and the same per-OS subprocess commands for everything the standard
library doesn't cover directly.
"""

from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import time
import webbrowser
from typing import Dict, List, Optional

import psutil

from core.logger import get_logger

logger = get_logger("system_control")
PLATFORM = platform.system()  # "Windows" | "Darwin" | "Linux"

_last_net: Optional[Dict[str, float]] = None

APP_LAUNCHERS: Dict[str, Dict[str, List[str]]] = {
    "chrome": {"Windows": ["start", "chrome"], "Darwin": ["open", "-a", "Google Chrome"], "Linux": ["xdg-open", "https://google.com"]},
    "spotify": {"Windows": ["start", "spotify"], "Darwin": ["open", "-a", "Spotify"], "Linux": ["xdg-open", "https://open.spotify.com"]},
    "discord": {"Windows": ["start", "discord"], "Darwin": ["open", "-a", "Discord"], "Linux": ["xdg-open", "https://discord.com/app"]},
    "vscode": {"Windows": ["code"], "Darwin": ["open", "-a", "Visual Studio Code"], "Linux": ["code"]},
    "steam": {"Windows": ["start", "steam"], "Darwin": ["open", "-a", "Steam"], "Linux": ["steam"]},
    "netflix": {"Windows": ["start", "https://netflix.com"], "Darwin": ["open", "https://netflix.com"], "Linux": ["xdg-open", "https://netflix.com"]},
    "youtube": {"Windows": ["start", "https://youtube.com"], "Darwin": ["open", "https://youtube.com"], "Linux": ["xdg-open", "https://youtube.com"]},
    "camera": {"Windows": ["start", "microsoft.windows.camera:"], "Darwin": ["open", "-a", "Photo Booth"], "Linux": ["cheese"]},
}


def _run(cmd: List[str]) -> None:
    shell = PLATFORM == "Windows" and cmd and cmd[0] == "start"
    subprocess.run(cmd, shell=shell, check=False, capture_output=True)


def open_app(name: str) -> str:
    key = name.lower().strip()
    launcher = APP_LAUNCHERS.get(key, {}).get(PLATFORM)
    if not launcher:
        if name.startswith("http://") or name.startswith("https://"):
            webbrowser.open(name)
            return f"Opened {name}"
        raise ValueError(f'I don\'t have a launcher registered for "{name}" on {PLATFORM}.')
    _run(launcher)
    return f"Opening {name}."


def media_control(action: str) -> str:
    try:
        if PLATFORM == "Darwin":
            key_codes = {"next": 124, "prev": 123, "play": 49, "pause": 49, "stop": 49}
            subprocess.run(["osascript", "-e", f'tell application "System Events" to key code {key_codes[action]}'], check=False)
        elif PLATFORM == "Linux":
            names = {"play": "play", "pause": "pause", "stop": "stop", "next": "next", "prev": "previous"}
            subprocess.run(["playerctl", names[action]], check=False)
        elif PLATFORM == "Windows":
            import keyboard  # type: ignore

            keys = {"play": "play/pause media", "pause": "play/pause media", "stop": "stop media", "next": "next track", "prev": "previous track"}
            keyboard.send(keys[action])
        return f"Media: {action}."
    except Exception as err:  # noqa: BLE001
        logger.warning("Media control failed: %s", err)
        raise RuntimeError(f"Couldn't send the {action} media command on this platform.") from err


def set_volume(percent: int) -> str:
    clamped = max(0, min(100, round(percent)))
    try:
        if PLATFORM == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {clamped}"], check=True)
        elif PLATFORM == "Linux":
            if shutil.which("pactl"):
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{clamped}%"], check=True)
            else:
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{clamped}%"], check=True)
        elif PLATFORM == "Windows":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(clamped / 100.0, None)
        return f"Volume set to {clamped}%."
    except Exception as err:  # noqa: BLE001
        logger.warning("Volume control failed: %s", err)
        raise RuntimeError("Couldn't change system volume on this platform.") from err


def set_brightness(percent: int) -> str:
    clamped = max(0, min(100, round(percent)))
    try:
        if PLATFORM == "Linux":
            if shutil.which("brightnessctl"):
                subprocess.run(["brightnessctl", "set", f"{clamped}%"], check=True)
            else:
                subprocess.run(["xbacklight", "-set", str(clamped)], check=True)
        else:
            import screen_brightness_control as sbc  # type: ignore

            sbc.set_brightness(clamped)
        return f"Brightness set to {clamped}%."
    except Exception as err:  # noqa: BLE001
        logger.warning("Brightness control failed: %s", err)
        raise RuntimeError("Brightness control isn't available on this device/platform.") from err


def power_action(action: str) -> str:
    cmds = {
        "shutdown": {"Windows": ["shutdown", "/s", "/t", "5"], "Darwin": ["osascript", "-e", 'tell app "System Events" to shut down'], "Linux": ["systemctl", "poweroff"]},
        "restart": {"Windows": ["shutdown", "/r", "/t", "5"], "Darwin": ["osascript", "-e", 'tell app "System Events" to restart'], "Linux": ["systemctl", "reboot"]},
    }
    _run(cmds[action][PLATFORM])
    return f"{'Shutting down' if action == 'shutdown' else 'Restarting'} in 5 seconds."


def check_internet_online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2.5)
        return True
    except OSError:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2.5)
            return True
        except OSError:
            return False


def collect_stats() -> Dict:
    global _last_net
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    net = psutil.net_io_counters()
    now = time.time()
    down_kbps = up_kbps = 0.0
    if _last_net:
        dt = max(now - _last_net["t"], 0.5)
        down_kbps = max(0.0, (net.bytes_recv - _last_net["rx"]) / dt / 1024)
        up_kbps = max(0.0, (net.bytes_sent - _last_net["tx"]) / dt / 1024)
    _last_net = {"rx": net.bytes_recv, "tx": net.bytes_sent, "t": now}

    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None

    temps = {}
    if hasattr(psutil, "sensors_temperatures"):
        try:
            temps = psutil.sensors_temperatures() or {}
        except Exception:  # noqa: BLE001
            temps = {}
    cpu_temp = None
    for entries in temps.values():
        if entries:
            cpu_temp = round(entries[0].current)
            break

    procs = []
    running = 0
    for p in psutil.process_iter(["name", "cpu_percent", "status"]):
        try:
            procs.append(p.info)
            if p.info.get("status") == psutil.STATUS_RUNNING:
                running += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top_by_cpu = sorted(procs, key=lambda p: p.get("cpu_percent") or 0, reverse=True)[:5]

    return {
        "timestamp": int(now * 1000),
        "cpu": {"loadPercent": round(cpu_percent, 1), "cores": psutil.cpu_count() or 1, "speedGhz": round((cpu_freq.current if cpu_freq else 0) / 1000, 2), "model": platform.processor() or "CPU"},
        "ram": {"usedGb": round(mem.used / 1024**3, 1), "totalGb": round(mem.total / 1024**3, 1), "usedPercent": round(mem.percent, 1)},
        "gpu": {"model": "N/A", "loadPercent": None, "vramUsedMb": None, "vramTotalMb": None},
        "battery": {
            "hasBattery": battery is not None,
            "percent": round(battery.percent) if battery else 0,
            "isCharging": bool(battery.power_plugged) if battery else False,
            "timeRemainingMin": (battery.secsleft // 60) if battery and battery.secsleft and battery.secsleft > 0 else None,
        },
        "storage": {"usedGb": round(disk.used / 1024**3, 1), "totalGb": round(disk.total / 1024**3, 1), "usedPercent": round(disk.percent, 1)},
        "network": {"interface": next(iter(psutil.net_if_addrs()), "n/a"), "downKbps": round(down_kbps), "upKbps": round(up_kbps), "online": True},
        "temperature": {"cpuC": cpu_temp},
        "processes": {
            "total": len(procs),
            "running": running,
            "topByCpu": [{"name": p.get("name") or "unknown", "cpuPercent": round(p.get("cpu_percent") or 0, 1)} for p in top_by_cpu],
        },
    }
