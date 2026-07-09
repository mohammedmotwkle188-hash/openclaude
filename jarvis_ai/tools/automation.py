"""Real mouse/keyboard control via pyautogui, plus vision-guided "click on X" targeting.

Python port of electron/services/system/automation.ts + electron/services/ai/vision.ts.
Same caveat as before: this gives Jarvis low-level hands (move, click, type, press,
scroll), not an autonomous planner — and vision-guided clicks are only as accurate as
the underlying model's ability to point at the right element in a screenshot.
"""

from __future__ import annotations

import base64
import io
import re
import sys
import time
from pathlib import Path
from typing import Optional

import pyautogui

from core.brain import ChatTurn, complete_once

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02

MODIFIER_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl",
    "cmd": "command", "command": "command", "super": "win", "win": "win",
    "alt": "alt", "option": "alt", "shift": "shift",
}

LOCATE_PROMPT = """You are a UI element locator. You will be shown a screenshot and a description of a UI
element on it. Respond with ONLY two numbers between 0 and 1, separated by a comma: the fractional
x,y position of the CENTER of that element, where (0,0) is the top-left corner and (1,1) is the
bottom-right corner of the image. No words, no explanation, no units — just "x,y".
If you cannot find the element, respond with exactly: not_found"""


def get_screen_size() -> tuple[int, int]:
    return pyautogui.size()


def move_to_fraction(x_frac: float, y_frac: float) -> tuple[int, int]:
    width, height = get_screen_size()
    x = round(max(0.0, min(1.0, x_frac)) * width)
    y = round(max(0.0, min(1.0, y_frac)) * height)
    pyautogui.moveTo(x, y, duration=0.15)
    return x, y


def click_at(x_frac: Optional[float] = None, y_frac: Optional[float] = None, button: str = "left") -> str:
    if x_frac is not None and y_frac is not None:
        move_to_fraction(x_frac, y_frac)
    pyautogui.click(button=button)
    return f"Clicked ({button})."


def double_click_at(x_frac: Optional[float] = None, y_frac: Optional[float] = None) -> str:
    if x_frac is not None and y_frac is not None:
        move_to_fraction(x_frac, y_frac)
    pyautogui.doubleClick()
    return "Double-clicked."


def scroll(direction: str, amount: int = 10) -> str:
    if direction == "up":
        pyautogui.scroll(amount)
    elif direction == "down":
        pyautogui.scroll(-amount)
    elif direction == "left":
        pyautogui.hscroll(-amount)
    else:
        pyautogui.hscroll(amount)
    return f"Scrolled {direction}."


def type_text(text: str) -> str:
    pyautogui.write(text, interval=0.01)
    return f'Typed "{text}".'


def press_key_combo(combo: str) -> str:
    parts = [p for p in re.split(r"[\s+]+", combo.lower().strip()) if p]
    keys = [MODIFIER_ALIASES.get(p, p) for p in parts]
    pyautogui.hotkey(*keys)
    return f"Pressed {combo}."


def hotkey(action: str) -> str:
    mod = "command" if sys.platform == "darwin" else "ctrl"
    mapping = {"copy": "c", "paste": "v", "cut": "x", "undo": "z", "redo": "y", "selectAll": "a"}
    pyautogui.hotkey(mod, mapping[action])
    label = "Selected all" if action == "selectAll" else action.capitalize() + "d"
    return f"{label}."


def capture_screenshot() -> str:
    out_dir = Path.home() / "Pictures" / "Jarvis Screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"jarvis-{int(time.time() * 1000)}.png"
    pyautogui.screenshot(str(path))
    return str(path)


def capture_screenshot_base64() -> dict:
    img = pyautogui.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"mimeType": "image/png", "base64": base64.b64encode(buf.getvalue()).decode()}


def locate_on_screen(description: str) -> tuple[float, float]:
    image = capture_screenshot_base64()
    text, _provider = complete_once(
        [ChatTurn(role="user", text=f'Find this element: "{description}"', image=image)],
        LOCATE_PROMPT,
    )
    cleaned = text.strip().lower()
    if "not_found" in cleaned:
        raise RuntimeError(f'Couldn\'t find "{description}" on screen.')
    match = re.search(r"(-?\d*\.?\d+)\s*,\s*(-?\d*\.?\d+)", cleaned)
    if not match:
        raise RuntimeError(f'Vision model returned an unreadable location for "{description}": "{text[:80]}"')
    x_frac = max(0.0, min(1.0, float(match.group(1))))
    y_frac = max(0.0, min(1.0, float(match.group(2))))
    return x_frac, y_frac


def click_on(description: str, button: str = "left") -> str:
    x_frac, y_frac = locate_on_screen(description)
    click_at(x_frac, y_frac, button=button)
    verb = "Right-clicked" if button == "right" else "Clicked"
    return f'{verb} on "{description}".'


def double_click_on(description: str) -> str:
    x_frac, y_frac = locate_on_screen(description)
    double_click_at(x_frac, y_frac)
    return f'Double-clicked on "{description}".'
