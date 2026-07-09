"""Tiny drop-in plugin system.

Put a Python file in the top-level PLUGINS/ folder that defines two things:

    PATTERN = r"^flip a coin$"          # a regex matched (case-insensitive) against your text
    def run(match):                      # match is the re.Match; return a string to speak
        import random
        return random.choice(["Heads.", "Tails."])

On startup every PLUGINS/*.py is loaded. When you type/say something, the orchestrator tries
each plugin's PATTERN before falling through to the Groq brain — so you can teach Jarvis new
commands just by dropping a file in, no edits to the core needed.

Fault-tolerant by design: a plugin that fails to import (or throws while running) is skipped
with one clean log line and never crashes Jarvis.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

PLUGINS_DIR = Path(__file__).resolve().parents[1] / "PLUGINS"


def _log(msg: str) -> None:
    print(f"[plugins] {msg}", flush=True)


@dataclass
class Plugin:
    name: str
    pattern: "re.Pattern[str]"
    run: Callable[[re.Match], str]


_loaded: List[Plugin] = []


def load_plugins() -> List[Plugin]:
    """Scan PLUGINS/ and load every valid *.py module. Safe to call once at startup."""
    _loaded.clear()
    if not PLUGINS_DIR.exists():
        return _loaded
    for path in sorted(PLUGINS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{path.stem}", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            pattern = getattr(module, "PATTERN", None)
            run = getattr(module, "run", None)
            if not isinstance(pattern, str) or not callable(run):
                _log(f"Skipped {path.name}: needs a PATTERN string and a run(match) function.")
                continue
            _loaded.append(Plugin(path.stem, re.compile(pattern, re.IGNORECASE), run))
            _log(f"Loaded plugin: {path.name}")
        except Exception as err:  # noqa: BLE001 - one bad plugin must not break the rest
            _log(f"Skipped {path.name}: {err}")
    return _loaded


def try_handle(text: str) -> Optional[str]:
    """If a loaded plugin matches the text, run it and return its reply. Else None."""
    for plugin in _loaded:
        m = plugin.pattern.match(text.strip())
        if m:
            try:
                result = plugin.run(m)
                return str(result) if result is not None else None
            except Exception as err:  # noqa: BLE001
                _log(f"Plugin {plugin.name} errored: {err}")
                return f"That command ({plugin.name}) ran into a problem."
    return None
