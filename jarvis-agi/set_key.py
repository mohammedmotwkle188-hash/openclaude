#!/usr/bin/env python3
"""Helper to save an API key from the terminal — no code to paste.

Two ways to use it:

  Interactive (menu):     python3 set_key.py
  One line (for scripts): python3 set_key.py groq gsk_yourkeyhere

Groq is the only key you actually need for chat.
"""

import json
import os
import sys

CONFIG = os.path.expanduser("~/.jarvis_agi/config.json")

PROVIDERS = ["groq", "openrouter", "gemini", "elevenlabs", "openweather", "newsapi"]


def _save(provider: str, key: str) -> None:
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
    try:
        os.chmod(CONFIG, 0o600)
    except OSError:
        pass
    print(f"\n✅ Saved your {provider} key ({len(key)} characters).")
    print("\nNow start Jarvis with:  ./start.sh   (or: python main.py)")


def main() -> None:
    # Non-interactive: `python3 set_key.py <provider> <key>`
    if len(sys.argv) >= 3:
        provider = sys.argv[1].lower().strip()
        key = sys.argv[2].strip()
        if provider not in PROVIDERS:
            print(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}")
            return
        if not key:
            print("No key given — nothing saved.")
            return
        _save(provider, key)
        return

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

    _save(provider, key)


if __name__ == "__main__":
    main()
