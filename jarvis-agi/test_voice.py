#!/usr/bin/env python3
"""Voice doctor — checks every part of the "Hi Jarvis" voice-input chain, one step at a
time, and tells you in plain words what is broken and how to fix it.

Run it from the jarvis-agi folder:

    ./.venv/bin/python test_voice.py

(or `source .venv/bin/activate` first, then `python test_voice.py`)
"""

import json
import os
import sys

GREEN = "\033[1;32m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[1;36m"
END = "\033[0m"


def ok(msg):   print(f"  {GREEN}✓ {msg}{END}")
def bad(msg):  print(f"  {RED}✗ {msg}{END}")
def note(msg): print(f"  {YELLOW}→ {msg}{END}")
def step(msg): print(f"\n{CYAN}STEP: {msg}{END}")


def fail_and_exit(*fix_lines):
    print(f"\n{RED}=================== HOW TO FIX IT ==================={END}")
    for line in fix_lines:
        print(f"  {line}")
    print(f"{RED}====================================================={END}")
    print("\nAfter fixing, run this test again:  ./.venv/bin/python test_voice.py\n")
    sys.exit(1)


def main():
    print("=" * 55)
    print("   JARVIS VOICE DOCTOR — finding why he can't hear you")
    print("=" * 55)

    # ------------------------------------------------------------------
    step("1/6  Is the speech library installed?")
    try:
        import speech_recognition as sr
        ok(f"SpeechRecognition {sr.__version__} is installed.")
    except ImportError:
        bad("SpeechRecognition is missing.")
        fail_and_exit(
            "Run these two lines:",
            "  cd ~/openclaude/jarvis-agi && source .venv/bin/activate",
            "  pip install -r requirements.txt",
        )

    # ------------------------------------------------------------------
    step("2/6  Is PyAudio (the microphone driver) installed?")
    try:
        import pyaudio
        ok("PyAudio is installed.")
    except ImportError:
        bad("PyAudio is missing — Jarvis has no way to reach a microphone.")
        fail_and_exit(
            "Run this line, then run this test again:",
            "  sudo apt install -y python3-pyaudio flac",
            "",
            "NOTE: if you created the .venv WITHOUT --system-site-packages, PyAudio from",
            "apt won't be visible. Easiest fix: re-run  ./install.sh  (it rebuilds it right).",
        )

    # ------------------------------------------------------------------
    step("3/6  Can Linux see ANY microphone?")
    pa = pyaudio.PyAudio()
    inputs = []
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if int(d.get("maxInputChannels", 0)) > 0:
            inputs.append(d.get("name", f"device {i}"))
    pa.terminate()
    if inputs:
        ok(f"Found {len(inputs)} input device(s): {', '.join(inputs[:4])}")
    else:
        bad("Linux sees NO microphone at all. This is the ChromeOS mic switch.")
        fail_and_exit(
            "1. Open ChromeOS Settings (the gear icon, NOT inside Linux).",
            "2. Search for the word:  Linux",
            "3. Open 'Linux development environment'.",
            "4. Turn ON:  'Allow Linux to access your microphone'.",
            "",
            "5. IMPORTANT: the switch only takes effect after Linux RESTARTS.",
            "   Right-click the Terminal icon on your shelf -> 'Shut down Linux',",
            "   then open the Terminal again. (Or just restart the Chromebook.)",
        )

    # ------------------------------------------------------------------
    step("4/6  Recording 4 seconds — SAY SOMETHING OUT LOUD NOW!")
    print("        (say:  'hello jarvis can you hear me'  ... recording)")

    def loudness(raw: bytes, width: int) -> int:
        # RMS without the audioop module (removed in Python 3.13)
        import array
        typecode = {1: "b", 2: "h", 4: "i"}.get(width, "h")
        samples = array.array(typecode, raw[: len(raw) - len(raw) % width])
        if not samples:
            return 0
        return int((sum(s * s for s in samples) / len(samples)) ** 0.5)

    try:
        rec = sr.Recognizer()
        with sr.Microphone() as source:
            rec.adjust_for_ambient_noise(source, duration=0.5)
            audio = rec.record(source, duration=4)
    except Exception as err:  # noqa: BLE001
        bad(f"Could not record: {err}")
        fail_and_exit(
            "The microphone exists but recording failed. Try:",
            "  1. Restart Linux (right-click Terminal icon -> Shut down Linux, reopen).",
            "  2. Run this test again.",
        )
    rms = loudness(audio.frame_data, audio.sample_width)
    if rms < 50:
        bad(f"Recorded — but it's SILENT (loudness {rms}). The mic isn't picking you up.")
        fail_and_exit(
            "Linux can open the mic but hears nothing. Check:",
            "  1. ChromeOS Settings -> search 'Linux' -> mic toggle is really ON.",
            "  2. Then SHUT DOWN Linux and reopen the Terminal (the toggle needs it).",
            "  3. Nothing is muted: click the clock (bottom-right) -> check mic isn't muted.",
            "  4. If you use headphones with a mic, try unplugging them.",
        )
    ok(f"Recorded real sound! (loudness {rms})")

    # ------------------------------------------------------------------
    step("5/6  Turning your words into text (needs internet)…")
    try:
        text = rec.recognize_google(audio)
        ok(f'Jarvis heard: "{text}"')
    except sr.UnknownValueError:
        note("Got sound but couldn't make out words — speak louder/closer and rerun.")
        text = None
    except Exception as err:  # noqa: BLE001
        bad(f"Speech service failed: {err}")
        fail_and_exit("This needs internet. Check WiFi, then run the test again.")

    # ------------------------------------------------------------------
    step("6/6  Is the Wake Word switch turned ON in Jarvis?")
    cfg_path = os.path.expanduser("~/.jarvis_agi/config.json")
    wake_on = False
    try:
        with open(cfg_path) as f:
            wake_on = bool(json.load(f).get("settings", {}).get("wakeWordEnabled"))
    except Exception:  # noqa: BLE001
        pass
    if wake_on:
        ok("Wake Word is ON in your settings.")
    else:
        note("Wake Word is OFF. Turning it ON for you now…")
        try:
            data = {}
            if os.path.exists(cfg_path):
                data = json.load(open(cfg_path))
            data.setdefault("settings", {})["wakeWordEnabled"] = True
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            json.dump(data, open(cfg_path, "w"), indent=2)
            ok("Done — Wake Word is now ON.")
        except Exception as err:  # noqa: BLE001
            bad(f"Couldn't update settings ({err}). Turn it on in the app's Settings gear.")

    # ------------------------------------------------------------------
    print(f"\n{GREEN}{'=' * 55}{END}")
    print(f"{GREEN}   ALL CHECKS PASSED — the microphone works! 🎉{END}")
    print(f"{GREEN}{'=' * 55}{END}")
    print("""
  Now do this:
    1. Start Jarvis:            ./start.sh
    2. Wait for the window.
    3. Say clearly:             "Jarvis, what's the time?"
       (say 'Jarvis' and the question in ONE sentence)

  Tip: he listens in short bursts. If he misses you, wait a
  second and say it again.
""")


if __name__ == "__main__":
    main()
