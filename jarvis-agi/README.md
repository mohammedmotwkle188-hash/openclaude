# JARVIS-AGI

A **lean, reliable** rebuild of the J.A.R.V.I.S. desktop assistant, tuned to actually run
on a low-spec Chromebook (ChromeOS Crostini Linux). Same holographic HUD you already saw,
a much simpler and sturdier backend, and **Groq** as the brain — a free, fast, official AI
service that works worldwide with no credit card.

This exists because the earlier build (`../jarvis_ai/`) technically ran but was painful in
practice: heavy dependencies (OpenCV, MediaPipe, PyAudio) fought the Chromebook's small
memory, and every AI key we tried had a problem (Gemini's free quota was `0`, ElevenLabs
returned 401, keys landed in the wrong slot). JARVIS-AGI removes all of that friction.

## Quick start (two commands)

Open the **Linux Terminal** on your Chromebook and run:

```bash
cd ~/openclaude && git pull        # get the latest code
cd jarvis-agi
chmod +x install.sh start.sh       # (first time only)
./install.sh                       # installs EVERYTHING, then asks for your Groq key
./start.sh                         # launches Jarvis
```

`install.sh` does the whole setup for you — system packages, the Python environment, all
dependencies, microphone support — and at the end it walks you through pasting a **free Groq
key** (get one at https://console.groq.com/keys — it starts with `gsk_`, no card needed).
It's safe to re-run any time (e.g. after a `git pull`).

In the blue J.A.R.V.I.S. window, type `hi` and press Enter — it replies and (if your
Chromebook's Linux audio is on) speaks in a British voice.

> Every time after that, just: `cd ~/openclaude/jarvis-agi && ./start.sh`

## What Jarvis can and can't do on a Chromebook

| ✅ Works on your Chromebook | ❌ Needs a real Windows / Mac PC |
| --- | --- |
| Chat & think (Groq brain, free) | Control ChromeOS windows / do your tasks for you |
| British voice replies | Create videos |
| "Hi Jarvis" voice input *(if mic enabled)* | Webcam / camera vision |
| Open apps & websites | Full email & calendar (OAuth) sign-in |
| File manager (list / open files) | Docker, ChromaDB, heavy RAG embeddings |
| Read & summarise PDFs | Mouse/keyboard automation |
| Play music / videos (YouTube, Spotify) | |
| Weather & news *(optional keys)* | |
| Timers, notes, jokes, volume | |
| Back up your data, update itself | |
| Long-term memory (remembers facts you tell it) | |
| Plugins (add your own commands) | |

The ❌ items are **hardware / sandbox limits of ChromeOS**, not missing code — the Linux
container can't reach your Chrome windows, camera, or the wider system. The full "controls
everything" Jarvis lives in `../jarvis_ai/` for a capable Windows/macOS/Linux machine.

## Things to say or type

- **Chat:** anything — "explain quantum computing", "write me a poem", "help me plan my week"
- **Files:** `list my downloads`, `show documents`, `open file report.pdf`
- **PDFs:** `read pdf invoice` → Jarvis extracts the text and summarises it
- **Media:** `play lofi beats on youtube`, `play daft punk on spotify`
- **Web:** `open youtube`, `search google for tallest mountain`
- **System:** `set volume to 40`, `what's the time`, `tell me a joke`
- **Memory:** `remember that my dog's name is Rex` → later ask "what's my dog's name?"
- **Maintenance:** `backup my data`, `update yourself`
- **Voice input** *(if you enabled the mic — see below)*: turn on **Wake Word** in Settings,
  then say "Jarvis, what's the time".

## Voice input ("Hi Jarvis") — optional

Voice replies work out of the box. To also **talk** to Jarvis:
1. ChromeOS **Settings → Advanced → Developers → Linux → "Allow Linux to access your
   microphone"** → ON.
2. `install.sh` already installed the mic packages (`python3-pyaudio`, `flac`).
3. Launch Jarvis, open **Settings** (gear), turn **Wake Word** ON, and say "Jarvis…".

If it doesn't hear you, the terminal prints a line starting with `[stt]` explaining why. The
mic in the Linux container can be unreliable — you can always just type.

## Plugins — teach Jarvis new commands

Drop a `.py` file into the `PLUGINS/` folder to add your own command — no core edits needed.
See `PLUGINS/README.md` and the `PLUGINS/example_hello.py` template (say **"say hello"** to
try it).

## Troubleshooting
- **No sound?** Make sure ChromeOS volume isn't muted; `install.sh` installs `mpg123`. Chat
  still works in text either way.
- **"No AI key set"** → run `python3 set_key.py groq gsk_YOURKEY` (or re-run `./install.sh`).
- **Window won't open?** Re-run `./install.sh`; it needs the GTK/WebKit packages.

## Project layout
```
jarvis-agi/
├── install.sh         one-command setup (apt + venv + deps + key)
├── start.sh           one-command launch
├── main.py            entry point
├── config.py          settings + keys (~/.jarvis_agi/config.json)
├── set_key.py         key helper (menu, or `set_key.py groq gsk_...`)
├── requirements.txt   lean deps
├── BRAIN/brain.py     Groq (+ OpenRouter/Gemini fallback), streaming
├── ENGINE/
│   ├── tts.py         edge-tts British voice -> mpg123 playback
│   └── stt.py         best-effort "Hi Jarvis" voice input
├── CORE/
│   ├── orchestrator.py  command-vs-chat routing, confirmation gate, plugin dispatch
│   ├── commands.py      apps, search, files, PDF, media, backup, update, weather, news, ...
│   ├── memory.py        SQLite history / facts / reminders + keyword recall
│   └── plugins.py       loads your PLUGINS/*.py
├── PLUGINS/           drop-in user commands (example + README)
└── UI/
    ├── dashboard.py   pywebview host + bridge
    └── web/           prebuilt holographic HUD
```

## Changelog vs. the older builds
- **New:** one-command `install.sh` + `start.sh` — no more manual apt/venv/pip steps.
- **New:** file manager, PDF reader (summarises via the brain), play music/video, data
  backup, self-update, and a drop-in **plugin system** — all Chromebook-safe.
- **New:** smarter memory — Jarvis recalls facts/notes relevant to what you ask.
- **New:** best-effort "Hi Jarvis" voice input (needs the ChromeOS mic toggle + PyAudio).
- **New:** Groq as the default free brain (fixes the "no working key" wall).
- **New:** command-line audio playback (`mpg123`/`ffplay`) so voice works on Crostini.
- **New:** "lite" HUD mode (animations off by default) for smooth rendering on low RAM.
- **Removed:** OpenCV, MediaPipe, pygame, cryptography and the features needing them — for a
  fast, reliable install on a small Chromebook.
- **Kept:** the holographic HUD, live stats, the safe command engine, and local memory.
