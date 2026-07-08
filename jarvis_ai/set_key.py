#!/usr/bin/env python3
"""Interactive helper to save an API key into Jarvis's config from the terminal.

For when the Settings gear is hard to reach (small/rotated screen, etc.). It asks which
service the key is for and then for the key itself — no code to paste, no long commands.

Run it with:  python set_key.py
"""

import json
import os

CONFIG = os.path.expanduser("~/.jarvis_ai/config.json")

PROVIDERS = [
    "gemini",
    "openai",
    "anthropic",
    "openrouter",
    "elevenlabs",
    "openweather",
    "newsapi",
    "wolfram",
]


def main() -> None:
    print("\nWhich service is this key for?\n")
    for i, name in enumerate(PROVIDERS, 1):
        print(f"  {i}. {name}")
    choice = input("\nType the number (e.g. 1 for gemini): ").strip().lower()

    if choice.isdigit() and 1 <= int(choice) <= len(PROVIDERS):
        provider = PROVIDERS[int(choice) - 1]
    elif choice in PROVIDERS:
        provider = choice
    else:
        print("\nDidn't recognise that choice. Run 'python set_key.py' again.")
        return

    key = input(f"\nPaste your {provider} key, then press Enter:\n> ").strip()
    if not key:
        print("\nNo key entered — nothing was saved.")
        return

    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    data = {}
    if os.path.exists(CONFIG):
        try:
            data = json.load(open(CONFIG))
        except Exception:  # noqa: BLE001 - a corrupt file just gets rewritten fresh
            data = {}
    data.setdefault("settings", {})
    data.setdefault("apiKeys", {})
    data["apiKeys"][provider] = key

    with open(CONFIG, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Saved your {provider} key ({len(key)} characters).")
    print("\nNow start Jarvis with:  python main.py")


if __name__ == "__main__":
    main()
