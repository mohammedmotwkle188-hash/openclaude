# Jarvis plugins

Teach Jarvis new commands by dropping a Python file in this folder. No changes to the core
code are needed — every `*.py` file here is loaded when Jarvis starts.

## How to write one

Each plugin file needs exactly two things:

```python
PATTERN = r"^flip a coin$"      # a regex, matched case-insensitively against your words

def run(match):                  # `match` is the regex match; return a string to speak
    import random
    return random.choice(["Heads.", "Tails."])
```

- **`PATTERN`** — a [regular expression](https://regexr.com). Use `(.+)` to capture words:
  `PATTERN = r"^count to (\d+)$"`, then read them with `match.group(1)` inside `run`.
- **`run(match)`** — do the work, `return` a sentence. Jarvis shows it and says it out loud.

## Rules

- One plugin per file. Files starting with `_` are ignored.
- Plugins are tried **before** the AI brain, so a matching plugin "wins".
- If a plugin has an error, Jarvis skips it with one log line and keeps running — it can
  never crash the app.
- After adding or editing a plugin, restart Jarvis (`./start.sh`) to load it.

See `example_hello.py` for a working template — say **"say hello"** to try it.
