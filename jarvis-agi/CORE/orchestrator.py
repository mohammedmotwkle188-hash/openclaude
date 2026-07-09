"""Central dispatch: turn a typed line into either a structured command or a Groq chat turn,
and push everything back to the HUD (and to speech). This is the trimmed successor to the
old orchestrator — same shape, far fewer moving parts.
"""

from __future__ import annotations

import datetime as dt
import re
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import config
from BRAIN import brain
from CORE import commands, memory, plugins
from ENGINE import tts


def _now() -> int:
    import time

    return int(time.time() * 1000)


@dataclass
class ParsedCommand:
    id: str
    raw: str
    action: str
    args: Dict[str, str]
    risk: str
    label: str


def _rules():
    return [
        (r"^open (chrome|youtube|spotify|netflix|discord|gmail|maps)$", "open_app", "safe",
         lambda m: f"Open {m.group(1)}", lambda m: {"app": m.group(1)}),
        (r"^search google for (.+)$", "search_google", "safe",
         lambda m: f"Search Google: {m.group(1)}", lambda m: {"query": m.group(1)}),
        (r"^search youtube for (.+)$", "search_youtube", "safe",
         lambda m: f"Search YouTube: {m.group(1)}", lambda m: {"query": m.group(1)}),
        (r"^set volume to (\d{1,3})%?$", "set_volume", "safe",
         lambda m: f"Set volume {m.group(1)}%", lambda m: {"percent": m.group(1)}),
        (r"^shut ?down(?: the)?(?: pc| computer)?$", "shutdown_pc", "confirm",
         lambda m: "Shut down this computer", lambda m: {}),
        (r"^restart(?: the)?(?: pc| computer)?$", "restart_pc", "confirm",
         lambda m: "Restart this computer", lambda m: {}),
        (r"^(?:what(?:'?s| is) the )?time\??$", "time", "safe", lambda m: "Time", lambda m: {}),
        (r"^(?:what(?:'?s| is) (?:the |today'?s )?date|what day is it)\??$", "date", "safe", lambda m: "Date", lambda m: {}),
        (r"^(?:tell me a joke|joke|say something funny)$", "joke", "safe", lambda m: "Joke", lambda m: {}),
        (r"^weather(?: in (.+))?$", "weather", "safe",
         lambda m: "Weather", lambda m: {"location": m.group(1) or ""}),
        (r"^news$", "news", "safe", lambda m: "News", lambda m: {}),
        (r"^(?:take a note|note|remember)(?:[:\-]| that| to)? (.+)$", "save_note", "safe",
         lambda m: f"Note: {m.group(1)[:30]}", lambda m: {"text": m.group(1)}),
        (r"^read (?:my )?(?:latest |last )?note$", "read_note", "safe", lambda m: "Read note", lambda m: {}),
        (r"^set (?:a )?timer for (\d+) (second|minute|hour)s?$", "timer", "safe",
         lambda m: f"Timer {m.group(1)} {m.group(2)}", lambda m: {"amount": m.group(1), "unit": m.group(2)}),
        # --- Chromebook-safe feature pack ---
        (r"^(?:list|show)(?: me)?(?: my)? (?:files (?:in )?)?(downloads?|documents|docs|desktop|pictures|photos|music|videos|home)$",
         "list_files", "safe", lambda m: f"List {m.group(1)}", lambda m: {"folder": m.group(1)}),
        (r"^open (?:the )?file (.+)$", "open_file", "safe",
         lambda m: f"Open file {m.group(1)[:24]}", lambda m: {"name": m.group(1)}),
        (r"^(?:read|summari[sz]e)(?: the)? pdf (.+)$", "read_pdf", "safe",
         lambda m: f"Read PDF {m.group(1)[:24]}", lambda m: {"name": m.group(1)}),
        (r"^play (.+?)(?: on (youtube|spotify))?$", "play", "safe",
         lambda m: f"Play {m.group(1)[:24]}", lambda m: {"query": m.group(1), "service": m.group(2) or "youtube"}),
        (r"^back ?up(?: my data| my stuff| everything)?$", "backup", "safe", lambda m: "Backup", lambda m: {}),
        (r"^(?:update yourself|update jarvis|check for updates)$", "self_update", "safe",
         lambda m: "Update", lambda m: {}),
    ]


def parse_command(raw: str) -> Optional[ParsedCommand]:
    text = raw.strip()
    for pattern, action, risk, label, args in _rules():
        m = re.match(pattern, text, re.IGNORECASE)
        if m:
            return ParsedCommand(str(uuid.uuid4()), text, action, args(m), risk, label(m))
    return None


DATA_ACTIONS = {"weather", "news"}


class Orchestrator:
    def __init__(self) -> None:
        self.push_event: Callable[[str, Any], None] = lambda ch, payload: None
        self.pending: Optional[ParsedCommand] = None
        self._abort = threading.Event()

    # --- entry point ---
    def handle_text(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self.push_event("chat_message", {"id": str(uuid.uuid4()), "role": "user", "text": text, "timestamp": _now()})

        cmd = parse_command(text)
        if cmd and cmd.action in DATA_ACTIONS:
            self._run_data(cmd)
            return
        if cmd and cmd.action == "read_pdf":
            self._run_pdf(cmd)
            return
        if cmd and cmd.risk == "confirm":
            self.pending = cmd
            self.push_event("confirmation_required", cmd.__dict__)
            return
        if cmd and cmd.risk == "safe":
            self._say(self._execute(cmd))
            return
        # No built-in command matched — give user plugins a chance before the AI brain.
        plugin_reply = plugins.try_handle(text)
        if plugin_reply is not None:
            self._say(plugin_reply)
            return
        self._run_chat(text)

    def confirm_pending(self) -> None:
        if self.pending:
            cmd, self.pending = self.pending, None
            self._say(self._execute(cmd))

    def cancel_pending(self) -> None:
        self.pending = None
        self.push_event("thought", {"text": "Cancelled.", "timestamp": _now()})

    def interrupt(self) -> None:
        self._abort.set()
        tts.stop_speaking()

    # --- helpers ---
    def _say(self, text: str) -> None:
        self.push_event("chat_message", {"id": str(uuid.uuid4()), "role": "assistant", "text": text, "timestamp": _now()})
        self.push_event("thought", {"text": text, "timestamp": _now()})
        memory.save_message("assistant", text)
        if config.get_settings()["voiceEnabled"]:
            self.push_event("voice_speaking_change", True)
            tts.speak(text)

    def _run_data(self, cmd: ParsedCommand) -> None:
        try:
            if cmd.action == "weather":
                w = commands.weather_data(cmd.args.get("location") or None)
                self._say(f"It's {w['tempC']}°C and {w['condition']} in {w['location']}, "
                          f"{w['humidityPercent']}% humidity.")
            else:
                items = commands.news_data()
                self._say("Top headlines: " + ". ".join(i["title"] for i in items[:3]) if items else "No headlines right now.")
        except Exception as err:  # noqa: BLE001
            self._say(str(err))

    def _run_pdf(self, cmd: ParsedCommand) -> None:
        name = cmd.args["name"]
        result = commands.read_pdf(name)
        # read_pdf returns either a short problem/hint message or the PDF's extracted text.
        problem_markers = ("I couldn't find", "PDF reading needs", "I couldn't read", "has no extractable")
        if any(result.startswith(m) for m in problem_markers):
            self._say(result)
            return
        # It's real text — ask the brain to summarise it.
        self.push_event("thought", {"text": f"Reading {name} …", "timestamp": _now()})
        prompt = f"Summarise this PDF ('{name}') clearly in a few sentences:\n\n{result}"
        self._stream_reply([brain.ChatTurn("user", prompt)])

    def _execute(self, cmd: ParsedCommand) -> str:
        try:
            return self._run_action(cmd)
        except Exception as err:  # noqa: BLE001
            return str(err) or f'Something went wrong with "{cmd.label}".'

    def _run_action(self, cmd: ParsedCommand) -> str:
        a, args = cmd.action, cmd.args
        if a == "open_app":
            return commands.open_app(args["app"])
        if a == "search_google":
            return commands.search_web("google", args["query"])
        if a == "search_youtube":
            return commands.search_web("youtube", args["query"])
        if a == "set_volume":
            return commands.set_volume(int(args["percent"]))
        if a == "shutdown_pc":
            return commands.power_action("shutdown")
        if a == "restart_pc":
            return commands.power_action("restart")
        if a == "time":
            return commands.tell_time()
        if a == "date":
            return commands.tell_date()
        if a == "joke":
            return commands.tell_joke()
        if a == "save_note":
            memory.remember_fact(f"note-{_now()}", args["text"])
            return "Noted."
        if a == "read_note":
            notes = [v for k, v in memory.recall_facts().items() if k.startswith("note-")]
            return f"Your latest note: {notes[-1]}" if notes else "You have no notes yet."
        if a == "timer":
            secs = int(args["amount"]) * {"second": 1, "minute": 60, "hour": 3600}[args["unit"]]
            self._start_timer(secs)
            return f"Timer set for {args['amount']} {args['unit']}(s)."
        if a == "list_files":
            return commands.list_files(args.get("folder"))
        if a == "open_file":
            return commands.open_file(args["name"])
        if a == "play":
            return commands.play(args["query"], args.get("service", "youtube"))
        if a == "backup":
            return commands.backup()
        if a == "self_update":
            return commands.self_update()
        raise ValueError(f"Unknown action {a}")

    def _start_timer(self, seconds: int) -> None:
        def fire():
            self.push_event("notification", {
                "id": str(uuid.uuid4()), "title": "Timer", "body": "Timer finished.",
                "level": "warning", "timestamp": _now(),
            })
            if config.get_settings()["voiceEnabled"]:
                tts.speak("Your timer has finished.")

        t = threading.Timer(seconds, fire)
        t.daemon = True
        t.start()

    def _run_chat(self, text: str) -> None:
        memory.save_message("user", text)
        self.push_event("thought", {"text": f'Thinking: "{text}"', "timestamp": _now()})
        turns = [brain.ChatTurn(m["role"], m["text"]) for m in memory.load_history(30)]
        self._stream_reply(turns, fact_lines=self._memory_context(text))

    def _memory_context(self, text: str) -> Optional[str]:
        """Build the 'things I remember' block: all durable facts + notes relevant to `text`."""
        lines: List[str] = []
        for k, v in memory.recall_facts().items():
            if not k.startswith("note-"):
                lines.append(f"- {k}: {v}")
        for k, v in memory.search_facts(text).items():
            if k.startswith("note-"):
                lines.append(f"- (a note you saved) {v}")
        return "\n".join(lines) or None

    def _stream_reply(self, turns: List["brain.ChatTurn"], fact_lines: Optional[str] = None) -> None:
        """Shared streaming path: push deltas to the HUD, then speak the full reply."""
        self._abort.clear()
        assistant_id = str(uuid.uuid4())
        self.push_event("chat_message", {"id": assistant_id, "role": "assistant", "text": "", "timestamp": _now(), "pending": True})

        def worker():
            collected: List[str] = []

            def on_delta(delta: str, _pid: str):
                if self._abort.is_set():
                    return
                collected.append(delta)
                self.push_event("chat_delta", {"id": assistant_id, "delta": delta, "provider": _pid})

            try:
                provider = brain.stream_with_fallback(turns, on_delta, fact_lines)
                full = "".join(collected)
                self.push_event("chat_done", {"id": assistant_id, "provider": provider})
                if full.strip():
                    memory.save_message("assistant", full, provider)
                    if config.get_settings()["voiceEnabled"] and not self._abort.is_set():
                        self.push_event("voice_speaking_change", True)
                        tts.speak(full)
            except Exception as err:  # noqa: BLE001
                self.push_event("chat_error", {"id": assistant_id, "error": str(err)})

        threading.Thread(target=worker, daemon=True).start()


orchestrator = Orchestrator()
