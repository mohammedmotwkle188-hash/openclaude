#!/usr/bin/env python3
"""Interactive helper to save an API key from the terminal — no code to paste.

Run:  python3 set_key.py
Then choose the service (Groq is #1 — the only key you actually need) and paste the key.
"""

import json
import os

CONFIG = os.path.expanduser("~/.jarvis_agi/config.json")

PROVIDERS = ["groq", "openrouter", "gemini", "elevenlabs", "openweather", "newsapi"]


def main() -> None:
    print("\nWhich service is this key for?\n")
    for i, name in enumerate(PROVIDERS, 1):
        star = "   <- the free key you need for chat" if name == "groq" else ""
        print(f"  {i}. {name}{star}")
    choice = input("\nType the number (1 for groq): ").strip().lower()

    if choice.isdigit() and 1 <= int(choice) <= len(PROVIDERS):
        provider = PROVIDERS[int(choice) - 1]
    elif choice in PROVIDERS:
        provider = choice
    else:
        print("\nDidn't recognise that. Run 'python3 set_key.py' again.")
        return

    key = input(f"\nPaste your {provider} key, then press Enter:\n> ").strip()
    if not key:
        print("\nNo key entered — nothing saved.")
        return

    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    data = {}
    if os.path.exists(CONFIG):
        try:
            data = json.load(open(CONFIG))
        except Exception:  # noqa: BLE001
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
