"""Central dispatch: turns a line of text (typed or spoken) into either a structured
command (open app, click, file op, ...) or a conversational AI turn, and pushes every
result back to the UI (and to speech) through a single push_event callback.

This is the Python equivalent of the Electron build's parser.ts + dispatcher.ts +
src/lib/commands/dispatch.ts combined into one place, since jarvis_ai has no separate
renderer process to split the work across.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import config
from core import brain
from core.logger import get_logger
from memory import long_term, short_term
from tools import automation, browser, files, system_control
from utils.helpers import new_id, now_ms
from voice import tts

logger = get_logger("orchestrator")

Rule = Dict[str, Any]


@dataclass
class ParsedCommand:
    id: str
    raw: str
    action: str
    args: Dict[str, str]
    risk: str
    label: str


def _rules() -> List[Rule]:
    return [
        {"pattern": r"^open (chrome|spotify|discord|vscode|vs code|steam|netflix|youtube|camera)$",
         "action": "open_app", "risk": "safe",
         "label": lambda m: f"Open {m.group(1)}", "args": lambda m: {"app": m.group(1).replace("vs code", "vscode")}},
        {"pattern": r"^(?:play|resume) music$", "action": "media_play", "risk": "safe", "label": lambda m: "Play music", "args": lambda m: {}},
        {"pattern": r"^stop music$", "action": "media_stop", "risk": "safe", "label": lambda m: "Stop music", "args": lambda m: {}},
        {"pattern": r"^pause music$", "action": "media_pause", "risk": "safe", "label": lambda m: "Pause music", "args": lambda m: {}},
        {"pattern": r"^next (?:track|song)$", "action": "media_next", "risk": "safe", "label": lambda m: "Next track", "args": lambda m: {}},
        {"pattern": r"^(?:previous|prev|last) (?:track|song)$", "action": "media_prev", "risk": "safe", "label": lambda m: "Previous track", "args": lambda m: {}},
        {"pattern": r"^shut ?down(?: the)?(?: pc| computer)?$", "action": "shutdown_pc", "risk": "confirm", "label": lambda m: "Shut down this computer", "args": lambda m: {}},
        {"pattern": r"^restart(?: the)?(?: pc| computer)?$", "action": "restart_pc", "risk": "confirm", "label": lambda m: "Restart this computer", "args": lambda m: {}},
        {"pattern": r"^search google for (.+)$", "action": "search_google", "risk": "safe", "label": lambda m: f"Search Google: {m.group(1)}", "args": lambda m: {"query": m.group(1)}},
        {"pattern": r"^search youtube for (.+)$", "action": "search_youtube", "risk": "safe", "label": lambda m: f"Search YouTube: {m.group(1)}", "args": lambda m: {"query": m.group(1)}},
        {"pattern": r"^set volume to (\d{1,3})%?$", "action": "set_volume", "risk": "safe", "label": lambda m: f"Set volume to {m.group(1)}%", "args": lambda m: {"percent": m.group(1)}},
        {"pattern": r"^set brightness to (\d{1,3})%?$", "action": "set_brightness", "risk": "safe", "label": lambda m: f"Set brightness to {m.group(1)}%", "args": lambda m: {"percent": m.group(1)}},
        {"pattern": r"^take (?:a )?screenshot$", "action": "screenshot", "risk": "safe", "label": lambda m: "Take a screenshot", "args": lambda m: {}},
        {"pattern": r"^open camera$", "action": "open_app", "risk": "safe", "label": lambda m: "Open camera", "args": lambda m: {"app": "camera"}},
        {"pattern": r"^open folder (.+)$", "action": "open_folder", "risk": "safe", "label": lambda m: f"Open folder {m.group(1)}", "args": lambda m: {"path": m.group(1)}},
        {"pattern": r"^create file (\S+)$", "action": "create_file", "risk": "safe", "label": lambda m: f"Create file {m.group(1)}", "args": lambda m: {"path": m.group(1)}},
        {"pattern": r"^delete file (\S+)$", "action": "delete_file", "risk": "confirm", "label": lambda m: f"Delete file {m.group(1)}", "args": lambda m: {"path": m.group(1)}},
        {"pattern": r"^move (\S+) to (\S+)$", "action": "move_file", "risk": "confirm", "label": lambda m: f"Move {m.group(1)} to {m.group(2)}", "args": lambda m: {"from": m.group(1), "to": m.group(2)}},
        {"pattern": r"^rename (\S+) to (\S+)$", "action": "rename_file", "risk": "safe", "label": lambda m: f"Rename {m.group(1)} to {m.group(2)}", "args": lambda m: {"path": m.group(1), "name": m.group(2)}},
        {"pattern": r"^weather(?: in (.+))?$", "action": "weather", "risk": "safe", "label": lambda m: f"Weather{' in ' + m.group(1) if m.group(1) else ''}", "args": lambda m: {"location": m.group(1) or ""}},
        {"pattern": r"^news$", "action": "news", "risk": "safe", "label": lambda m: "Latest headlines", "args": lambda m: {}},
        {"pattern": r"^stock(?:s)? (?:price )?(?:for |of )?([A-Za-z.]{1,6})$", "action": "stock", "risk": "safe", "label": lambda m: f"Stock price: {m.group(1).upper()}", "args": lambda m: {"symbol": m.group(1)}},
        {"pattern": r"^crypto(?: price)? (?:for |of )?(\w{2,10})$", "action": "crypto", "risk": "safe", "label": lambda m: f"Crypto price: {m.group(1).upper()}", "args": lambda m: {"symbol": m.group(1)}},
        {"pattern": r"^(?:double[- ]click) (?:on |the )(.+)$", "action": "double_click_on", "risk": "safe", "label": lambda m: f'Double-click on "{m.group(1)}"', "args": lambda m: {"target": m.group(1)}},
        {"pattern": r"^(?:double[- ]click)$", "action": "double_click", "risk": "safe", "label": lambda m: "Double-click", "args": lambda m: {}},
        {"pattern": r"^right[- ]click (?:on |the )(.+)$", "action": "right_click_on", "risk": "safe", "label": lambda m: f'Right-click on "{m.group(1)}"', "args": lambda m: {"target": m.group(1)}},
        {"pattern": r"^right[- ]click$", "action": "right_click", "risk": "safe", "label": lambda m: "Right-click", "args": lambda m: {}},
        {"pattern": r"^(?:click|tap) (?:on |the )(.+)$", "action": "click_on", "risk": "safe", "label": lambda m: f'Click on "{m.group(1)}"', "args": lambda m: {"target": m.group(1)}},
        {"pattern": r"^(?:click|tap)$", "action": "click", "risk": "safe", "label": lambda m: "Click", "args": lambda m: {}},
        {"pattern": r"^type (.+)$", "action": "type_text", "risk": "safe", "label": lambda m: f'Type "{m.group(1)}"', "args": lambda m: {"text": m.group(1)}},
        {"pattern": r"^press (.+)$", "action": "press_key", "risk": "safe", "label": lambda m: f"Press {m.group(1)}", "args": lambda m: {"combo": m.group(1)}},
        {"pattern": r"^scroll (up|down|left|right)$", "action": "scroll", "risk": "safe", "label": lambda m: f"Scroll {m.group(1)}", "args": lambda m: {"direction": m.group(1).lower()}},
        {"pattern": r"^copy$", "action": "hotkey_copy", "risk": "safe", "label": lambda m: "Copy", "args": lambda m: {}},
        {"pattern": r"^paste$", "action": "hotkey_paste", "risk": "safe", "label": lambda m: "Paste", "args": lambda m: {}},
        {"pattern": r"^cut$", "action": "hotkey_cut", "risk": "safe", "label": lambda m: "Cut", "args": lambda m: {}},
        {"pattern": r"^undo$", "action": "hotkey_undo", "risk": "safe", "label": lambda m: "Undo", "args": lambda m: {}},
        {"pattern": r"^redo$", "action": "hotkey_redo", "risk": "safe", "label": lambda m: "Redo", "args": lambda m: {}},
        {"pattern": r"^select all$", "action": "hotkey_selectall", "risk": "safe", "label": lambda m: "Select all", "args": lambda m: {}},

        # Computer vision (webcam)
        {"pattern": r"^(?:who (?:is|am i)|who do you see|recogni[sz]e (?:my |the )?face)\??$", "action": "recognize_face", "risk": "safe", "label": lambda m: "Recognize face", "args": lambda m: {}},
        {"pattern": r"^learn my face as (.+)$", "action": "enroll_face", "risk": "safe", "label": lambda m: f"Learn face as {m.group(1)}", "args": lambda m: {"name": m.group(1)}},
        {"pattern": r"^(?:what gesture|read my hand|detect (?:my )?gesture)\??$", "action": "detect_gesture", "risk": "safe", "label": lambda m: "Detect hand gesture", "args": lambda m: {}},
        {"pattern": r"^(?:check my eyes|am i looking|track my eyes)\??$", "action": "check_eyes", "risk": "safe", "label": lambda m: "Check eyes", "args": lambda m: {}},

        # Knowledge / STEM / calendar. Deliberately only explicit compute verbs, not a broad
        # "what is ..." — general questions should reach the conversational AI, which handles
        # them better, rather than being force-routed to Wolfram.
        {"pattern": r"^(?:calculate|compute|solve|how much is) (.+)$", "action": "wolfram", "risk": "safe", "label": lambda m: f"Compute: {m.group(1)}", "args": lambda m: {"query": m.group(1)}},
        {"pattern": r"^(?:my calendar|upcoming events|what'?s on my calendar|read (?:my )?calendar)\??$", "action": "calendar_read", "risk": "safe", "label": lambda m: "Read calendar", "args": lambda m: {}},

        # Offline utilities
        {"pattern": r"^(?:take a note|note|remember)(?:[:\-]| that| to)? (.+)$", "action": "save_note", "risk": "safe", "label": lambda m: f"Save note: {m.group(1)[:30]}", "args": lambda m: {"text": m.group(1)}},
        {"pattern": r"^read (?:my )?(?:latest |last )?note$", "action": "read_note", "risk": "safe", "label": lambda m: "Read latest note", "args": lambda m: {}},
        {"pattern": r"^(?:tell me a joke|say something funny|joke)$", "action": "joke", "risk": "safe", "label": lambda m: "Tell a joke", "args": lambda m: {}},
        {"pattern": r"^(?:what(?:'?s| is) the )?time\??$", "action": "time", "risk": "safe", "label": lambda m: "Tell the time", "args": lambda m: {}},
        {"pattern": r"^(?:what(?:'?s| is) (?:the |today'?s )?date|what day is it)\??$", "action": "date", "risk": "safe", "label": lambda m: "Tell the date", "args": lambda m: {}},
        {"pattern": r"^set (?:a )?timer for (\d+) (second|minute|hour)s?$", "action": "timer", "risk": "safe", "label": lambda m: f"Timer for {m.group(1)} {m.group(2)}(s)", "args": lambda m: {"amount": m.group(1), "unit": m.group(2)}},

        # Smart-home (Philips Hue). "all lights" must be tested before the named-light rule,
        # otherwise the greedy name capture swallows "all" as if it were a light's name.
        {"pattern": r"^pair (?:the )?(?:lights|hue)$", "action": "hue_pair", "risk": "safe", "label": lambda m: "Pair Hue bridge", "args": lambda m: {}},
        {"pattern": r"^turn (on|off) (?:the |all )?lights$", "action": "hue_set_all", "risk": "safe", "label": lambda m: f"Turn {m.group(1)} all lights", "args": lambda m: {"on": m.group(1)}},
        {"pattern": r"^turn (on|off) (?:the )?(.+?) light?s?$", "action": "hue_set", "risk": "safe", "label": lambda m: f"Turn {m.group(1)} {m.group(2)} light", "args": lambda m: {"on": m.group(1), "name": m.group(2)}},
    ]


def parse_command(raw: str) -> Optional[ParsedCommand]:
    text = raw.strip()
    for rule in _rules():
        m = re.match(rule["pattern"], text, re.IGNORECASE)
        if m:
            return ParsedCommand(new_id(), text, rule["action"], rule["args"](m), rule["risk"], rule["label"](m))
    return None


DATA_ACTIONS = {"weather", "news", "stock", "crypto"}


class Orchestrator:
    def __init__(self) -> None:
        self.push_event: Callable[[str, Any], None] = lambda channel, payload: None
        self.pending_confirmation: Optional[ParsedCommand] = None
        self._abort = threading.Event()

    # --- outward-facing entry points, called from the UI bridge or the wake-word thread ---

    def handle_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self.push_event("chat_message", {"id": new_id(), "role": "user", "text": text, "timestamp": now_ms()})

        parsed = parse_command(text)
        if parsed and parsed.action in DATA_ACTIONS:
            self._run_data_action(parsed)
            return
        if parsed and parsed.risk == "confirm":
            self.pending_confirmation = parsed
            self.push_event("confirmation_required", parsed.__dict__)
            return
        if parsed and parsed.risk == "safe":
            result = self._execute(parsed)
            self._say(result)
            return

        self._run_chat(text)

    def confirm_pending(self) -> None:
        if not self.pending_confirmation:
            return
        cmd = self.pending_confirmation
        self.pending_confirmation = None
        result = self._execute(cmd)
        self._say(result)

    def cancel_pending(self) -> None:
        self.pending_confirmation = None
        self.push_event("thought", {"text": "Confirmation cancelled.", "timestamp": now_ms()})

    def interrupt(self) -> None:
        self._abort.set()
        tts.stop_speaking()

    def analyze_screen(self, question: str = "What's currently on my screen? Describe it and answer anything notable.") -> None:
        image = automation.capture_screenshot_base64()
        self.push_event("chat_message", {"id": new_id(), "role": "user", "text": f"[screenshot attached] {question}", "timestamp": now_ms()})
        self._run_chat(question, image=image)

    # --- internals ---

    def _say(self, text: str) -> None:
        msg_id = new_id()
        self.push_event("chat_message", {"id": msg_id, "role": "assistant", "text": text, "timestamp": now_ms()})
        self.push_event("thought", {"text": text, "timestamp": now_ms()})
        short_term.add("assistant", text)
        long_term.save_message("assistant", text, None)
        if config.get_settings()["voiceEnabled"]:
            tts.speak(text, config.get_settings())

    def _run_chat(self, text: str, image: Optional[Dict[str, str]] = None) -> None:
        self._abort.clear()
        short_term.add("user", text)
        long_term.save_message("user", text, None)

        assistant_id = new_id()
        self.push_event("chat_message", {"id": assistant_id, "role": "assistant", "text": "", "timestamp": now_ms(), "pending": True})
        self.push_event("thought", {"text": f'Thinking about: "{text}"', "timestamp": now_ms()})

        def worker():
            turns = short_term.get_turns()
            if image and turns:
                turns[-1].image = image
            facts = long_term.recall_facts()
            fact_lines = "\n".join(f"- {k}: {v}" for k, v in facts.items()) if facts else None

            full: List[str] = []

            def on_delta(delta: str, provider: str):
                if self._abort.is_set():
                    return
                full.append(delta)
                self.push_event("chat_delta", {"id": assistant_id, "delta": delta, "provider": provider})

            try:
                provider = brain.stream_with_fallback(turns, on_delta, fact_lines)
                full_text = "".join(full)
                self.push_event("chat_done", {"id": assistant_id, "provider": provider})
                if full_text.strip():
                    short_term.add("assistant", full_text)
                    long_term.save_message("assistant", full_text, provider)
                    if config.get_settings()["voiceEnabled"] and not self._abort.is_set():
                        tts.speak(full_text, config.get_settings())
            except Exception as err:  # noqa: BLE001
                logger.exception("Chat failed")
                self.push_event("chat_error", {"id": assistant_id, "error": str(err)})

        threading.Thread(target=worker, daemon=True).start()

    def _run_data_action(self, cmd: ParsedCommand) -> None:
        from tools import webdata

        try:
            if cmd.action == "weather":
                w = webdata.fetch_weather(cmd.args.get("location") or None)
                self._say(f"It's currently {w['tempC']}°C and {w['condition']} in {w['location']}, with {w['humidityPercent']}% humidity.")
            elif cmd.action == "news":
                headlines = webdata.fetch_news()
                if not headlines:
                    self._say("No headlines available right now.")
                else:
                    self._say("Top headlines: " + ". ".join(h["title"] for h in headlines[:3]))
            elif cmd.action == "stock":
                self._say(webdata.fetch_stock_quote(cmd.args["symbol"]))
            elif cmd.action == "crypto":
                self._say(webdata.fetch_crypto_price(cmd.args["symbol"]))
        except Exception as err:  # noqa: BLE001
            self._say(str(err) or "That data source isn't available right now.")

    def _execute(self, cmd: ParsedCommand) -> str:
        try:
            return self._run_action(cmd)
        except Exception as err:  # noqa: BLE001
            logger.exception("Command failed: %s", cmd.action)
            return str(err) or f'Something went wrong running "{cmd.label}".'

    def _run_action(self, cmd: ParsedCommand) -> str:
        a = cmd.action
        args = cmd.args
        if a == "open_app":
            return system_control.open_app(args["app"])
        if a == "media_play":
            return system_control.media_control("play")
        if a == "media_pause":
            return system_control.media_control("pause")
        if a == "media_stop":
            return system_control.media_control("stop")
        if a == "media_next":
            return system_control.media_control("next")
        if a == "media_prev":
            return system_control.media_control("prev")
        if a == "shutdown_pc":
            return system_control.power_action("shutdown")
        if a == "restart_pc":
            return system_control.power_action("restart")
        if a == "search_google":
            return browser.search_web("google", args["query"])
        if a == "search_youtube":
            return browser.search_web("youtube", args["query"])
        if a == "set_volume":
            return system_control.set_volume(int(args["percent"]))
        if a == "set_brightness":
            return system_control.set_brightness(int(args["percent"]))
        if a == "screenshot":
            return f"Screenshot saved to {automation.capture_screenshot()}"
        if a == "open_folder":
            return files.open_folder(args["path"])
        if a == "create_file":
            return files.create_file(args["path"])
        if a == "delete_file":
            return files.delete_file(args["path"])
        if a == "move_file":
            return files.move_file(args["from"], args["to"])
        if a == "rename_file":
            return files.rename_file(args["path"], args["name"])
        if a == "click":
            return automation.click_at()
        if a == "click_on":
            return automation.click_on(args["target"])
        if a == "double_click":
            return automation.double_click_at()
        if a == "double_click_on":
            return automation.double_click_on(args["target"])
        if a == "right_click":
            return automation.click_at(button="right")
        if a == "right_click_on":
            return automation.click_on(args["target"], button="right")
        if a == "type_text":
            return automation.type_text(args["text"])
        if a == "press_key":
            return automation.press_key_combo(args["combo"])
        if a == "scroll":
            return automation.scroll(args["direction"])
        if a == "hotkey_copy":
            return automation.hotkey("copy")
        if a == "hotkey_paste":
            return automation.hotkey("paste")
        if a == "hotkey_cut":
            return automation.hotkey("cut")
        if a == "hotkey_undo":
            return automation.hotkey("undo")
        if a == "hotkey_redo":
            return automation.hotkey("redo")
        if a == "hotkey_selectall":
            return automation.hotkey("selectAll")

        # --- Computer vision (webcam) ---
        if a == "recognize_face":
            from vision import face

            return face.recognize_face()
        if a == "enroll_face":
            from vision import face

            return face.enroll_face(args["name"])
        if a == "detect_gesture":
            from vision import gestures

            return gestures.detect_gesture()
        if a == "check_eyes":
            from vision import eyetracking

            return eyetracking.check_eyes()

        # --- Knowledge / calendar ---
        if a == "wolfram":
            from tools import wolfram

            return wolfram.ask_wolfram(args["query"])
        if a == "calendar_read":
            from tools import calendar_google

            return calendar_google.summarize_upcoming()

        # --- Offline utilities ---
        if a == "save_note":
            from tools import notes

            return notes.save_note(args["text"])
        if a == "read_note":
            from tools import notes

            return notes.read_latest_note()
        if a == "joke":
            from tools import jokes

            return jokes.tell_joke()
        if a == "time":
            import datetime as _dt

            return f"It's {_dt.datetime.now().strftime('%H:%M')}."
        if a == "date":
            import datetime as _dt

            return f"Today is {_dt.datetime.now().strftime('%A, %d %B %Y')}."
        if a == "timer":
            from tools import timers

            unit_seconds = {"second": 1, "minute": 60, "hour": 3600}[args["unit"]]
            return timers.start_timer(int(args["amount"]) * unit_seconds, "Timer")

        # --- Smart-home (Philips Hue) ---
        if a == "hue_pair":
            from tools import iot

            return iot.pair_hue_bridge()
        if a == "hue_set":
            from tools import iot

            return iot.set_light(args["name"], args["on"] == "on")
        if a == "hue_set_all":
            from tools import iot

            return iot.set_light(None, args["on"] == "on")

        raise ValueError(f'Unknown action "{a}".')


orchestrator = Orchestrator()
