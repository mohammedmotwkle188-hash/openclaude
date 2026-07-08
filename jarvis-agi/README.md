# JARVIS-AGI

A **lean, reliable** rebuild of the J.A.R.V.I.S. desktop assistant, tuned to actually run
on a low-spec Chromebook (ChromeOS Crostini Linux). Same holographic HUD you already saw,
a much simpler and sturdier backend, and **Groq** as the brain — a free, fast, official AI
service that works worldwide with no credit card.

This exists because the earlier build (`../jarvis_ai/`) technically ran but was painful in
practice: heavy dependencies (OpenCV, MediaPipe, PyAudio) fought the Chromebook's small
memory, and every AI key we tried had a problem (Gemini's free quota was `0`, ElevenLabs
returned 401, keys landed in the wrong slot). JARVIS-AGI removes all of that friction.

## What it does

- **Chat brain: Groq** (free key from console.groq.com, model `llama-3.3-70b-versatile`),
  with OpenRouter and Gemini as optional fallbacks. You only need the Groq key.
- **Holographic HUD** — the same radar/orb interface, served locally via pywebview (no
  Electron, no bundled Chromium).
- **Live system stats** — CPU, RAM, battery, storage via `psutil`.
- **British voice output** — free Microsoft Edge neural voice (`en-GB-RyanNeural`), played
  through `mpg123` (the reliable audio path on Crostini). ElevenLabs is optional.
- **Commands** — open apps/sites, Google/YouTube search, volume, time, date, jokes, notes,
  timers, and (with optional keys) weather & news. Shutdown/restart ask for confirmation.
- **Local memory** — chat history, facts, and reminders in a small SQLite file.

## What's intentionally left out (and why)

Webcam vision (face/gesture/eye), microphone voice input, mouse/keyboard automation,
screen OCR, Wolfram, Google Calendar, and smart-home control are **not** in this build.
They can't work on this Chromebook (no usable camera/mic in the Linux container, tiny RAM)
and they were the main cause of the earlier install failures. They still live in the
`../jarvis_ai/` build for a more capable Windows/macOS/Linux machine.

## Setup — Chromebook (ChromeOS Linux / Crostini), step by step

Open the **Linux Terminal** and run these one at a time:

```bash
# 1. System pieces (the HUD window + audio player)
sudo apt update
sudo apt install -y python3 python3-venv git python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 mpg123

# 2. Get the code
cd ~/openclaude && git pull      # or: git clone <repo> && cd openclaude
cd jarvis-agi

# 3. Create + activate the environment (system-site-packages lets it see the GTK bits)
python3 -m venv .venv --system-site-packages
source .venv/bin/activate

# 4. Install the (few) Python dependencies
pip install -r requirements.txt

# 5. Get a FREE Groq key at  https://console.groq.com/keys  (it starts with "gsk_")
python3 set_key.py               # choose 1 (groq), paste the key

# 6. Run it
python main.py
```

Then in the blue J.A.R.V.I.S. window, type `hi` in the bottom box and press Enter — it
replies, and (if your Chromebook's Linux audio is on) speaks in a British voice.

> **Every time you start it again:** `cd ~/openclaude/jarvis-agi && source .venv/bin/activate && python main.py`

### Notes / troubleshooting
- **`(.venv)` must show** at the start of your prompt before `python main.py`. If not, run
  `source .venv/bin/activate` first.
- **No sound?** Make sure the ChromeOS volume (click the clock) isn't muted. `mpg123` must
  be installed (step 1). Chat still works in text even if audio doesn't.
- **"No AI key set"** in chat → run `python3 set_key.py` and add your Groq key (step 5).
- You do **not** need a microphone — you type to Jarvis; it can talk back.

## Project layout
```
jarvis-agi/
├── main.py            entry point
├── config.py          settings + keys (~/.jarvis_agi/config.json)
├── set_key.py         interactive key helper
├── requirements.txt   lean deps
├── BRAIN/brain.py     Groq (+ OpenRouter/Gemini fallback), streaming
├── ENGINE/tts.py      edge-tts British voice -> mpg123 playback
├── CORE/
│   ├── orchestrator.py  command-vs-chat routing, confirmation gate
│   ├── commands.py      apps, search, volume, time, jokes, weather, news, ...
│   └── memory.py        SQLite history / facts / reminders
└── UI/
    ├── dashboard.py   pywebview host + bridge
    └── web/           prebuilt holographic HUD
```

## Changelog vs. the older builds
- **New:** Groq as the default free brain (fixes the "no working key" wall).
- **New:** command-line audio playback (`mpg123`/`ffplay`) so voice works on Crostini,
  where pygame/SDL couldn't find an audio device.
- **New:** clean multi-provider error reporting (shows the real reason each provider failed).
- **Removed:** OpenCV, MediaPipe, PyAudio, pygame, cryptography and the features needing
  them — for a fast, reliable install on a small Chromebook.
- **Kept:** the holographic HUD, live stats, the safe command engine, and local memory.
