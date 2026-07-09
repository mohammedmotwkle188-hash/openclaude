"""Example Jarvis plugin. Copy this file, change PATTERN and run(), and drop it in this
folder to teach Jarvis a brand-new command — no changes to the core code needed.

Try saying/typing:  say hello
"""

# A regex matched (case-insensitive) against what you type or say.
PATTERN = r"^say hello$"


def run(match):
    """Return a string; Jarvis will show it and speak it."""
    return "Hello! I'm Jarvis, running from a plugin you can edit yourself."
