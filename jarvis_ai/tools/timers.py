"""In-memory alarms / timers that fire a callback (used to push a notification + speak)
when they elapse. Backed by threading.Timer, so they only live as long as the app runs —
persistent reminders that survive a restart already live in memory/long_term.py.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from utils.helpers import new_id, now_ms


@dataclass
class ActiveTimer:
    id: str
    label: str
    fire_at_ms: int
    handle: threading.Timer = field(repr=False)


_timers: Dict[str, ActiveTimer] = {}
_on_fire: Optional[Callable[[str, str], None]] = None


def set_fire_callback(cb: Callable[[str, str], None]) -> None:
    """cb(timer_id, label) is invoked on the main-app side when a timer elapses."""
    global _on_fire
    _on_fire = cb


def start_timer(seconds: float, label: str = "Timer") -> str:
    timer_id = new_id()

    def fire() -> None:
        _timers.pop(timer_id, None)
        if _on_fire:
            _on_fire(timer_id, label)

    handle = threading.Timer(seconds, fire)
    handle.daemon = True
    handle.start()
    _timers[timer_id] = ActiveTimer(timer_id, label, now_ms() + int(seconds * 1000), handle)

    mins = int(seconds // 60)
    secs = int(seconds % 60)
    human = f"{mins} min {secs} sec" if mins else f"{secs} seconds"
    return f"{label} set for {human} from now."


def cancel_timer(timer_id: str) -> bool:
    timer = _timers.pop(timer_id, None)
    if timer:
        timer.handle.cancel()
        return True
    return False


def list_timers() -> List[Dict]:
    now = now_ms()
    return [
        {"id": t.id, "label": t.label, "remainingSec": max(0, (t.fire_at_ms - now) // 1000)}
        for t in _timers.values()
    ]
