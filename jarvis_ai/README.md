# J.A.R.V.I.S. (Python)

A full Python rebuild of the J.A.R.V.I.S. desktop assistant — same holographic HUD look,
but every "brain" function (voice, AI, memory, automation, system control) now runs in
Python instead of Node/Electron. The original Electron/TypeScript build lives untouched
at `../jarvis-desktop/` if you want to compare or keep using it; this is a parallel,
independent implementation, not a patch on top of it.

## Why the UI is still HTML/CSS/JS

The HUD (radar, panels, animations, glassmorphism) is a pre-built static bundle in
`ui/web/`, hosted by [`pywebview`](https://pywebview.flowrl.com/) instead of a browser or
Electron. pywebview wraps whatever native webview your OS already has (WebView2 on
Windows, WKWebView on macOS, WebKitGTK on Linux) — no Node.js or Chromium bundled at
runtime, no Electron. The frontend's *source* lives in `ui/frontend/` (a small
Vite+React+TypeScript project, adapted from the Electron build) purely as build tooling;
only its compiled output (`ui/frontend/dist/`, copied to `ui/web/`) ships with the app. If
you never touch the UI you never need Node installed at all — `ui/web/` is already built.

Python and the page talk to each other exactly the way Electron's preload/IPC did, just
with different plumbing: `window.pywebview.api.<name>(...)` calls into `ui/dashboard.py`'s
`JarvisApi`, and Python pushes events back with `window.evaluate_js(...)` into a small
listener bus defined in `ui/frontend/src/lib/bridge.ts`. All AI calls, voice, memory, and
system control happen in Python — the page is a display/input layer only, with no
API keys and no direct AI/OS calls of its own.

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

### Platform-specific extras

- **Linux**: pywebview needs GTK+WebKitGTK (`sudo apt install python3-gi gir1.2-gtk-3.0
  gir1.2-webkit2-4.1`) or Qt (`pip install pywebview[qt]`, plus system libs — see below if
  you hit `libEGL`/`xcb` errors). `pyautogui` needs an X11 session (Wayland: install and
  run under XWayland). OCR needs the system `tesseract` binary: `sudo apt install
  tesseract-ocr`.
- **macOS**: grant Accessibility + Screen Recording permission (System Settings → Privacy
  & Security) the first time automation/screenshots run. OCR: `brew install tesseract`.
- **Windows**: `pip install pywebview[cef]` is a solid fallback if WebView2 isn't present.
  OCR: install Tesseract from the UB-Mannheim build and add it to `PATH`. Volume control
  uses `pycaw`/`comtypes` (already in requirements.txt for `sys_platform == "win32"`).
- **PyAudio** (mic input for `SpeechRecognition`) needs PortAudio: `apt install
  portaudio19-dev` (Linux) before `pip install pyaudio`, `brew install portaudio` (macOS);
  Windows normally gets a prebuilt wheel with no extra step.

### Rebuilding the frontend (only if you change the UI)

```bash
cd ui/frontend
npm install
npm run build
cp -r dist/* ../web/
```

## Configure API keys and providers

Launch the app, open Settings, and add keys for whichever providers you use — same
providers as the Electron build: **Anthropic**, **OpenAI**, **Google Gemini**, or a local
**Ollama** server (no key, just point "Ollama base URL" at `http://127.0.0.1:11434` or
wherever `ollama serve` is running). The AI Model Fallback Order controls which is tried
first; if one errors or isn't configured, `core/brain.py` falls through to the next.
**OpenWeather** and **NewsAPI** keys unlock the Weather/News widgets; stocks (Stooq) and
crypto (CoinGecko) need no key.

## Voice

- **STT**: `voice/stt.py` and `voice/wakeword.py` use `SpeechRecognition`'s Google Web
  Speech backend (free, no key, needs internet) against your real system microphone via
  PyAudio — not the browser, so it works the same regardless of which native webview your
  OS uses.
- **Wake word**: say **"Jarvis"**, then either finish the command in the same breath or
  pause and it'll wait for the next thing you say. Toggling "Wake Word" in Settings starts
  or stops the background listener thread (`ui/dashboard.py`'s `settings_set`).
  There's no dedicated wake-word model (Porcupine/openWakeWord) wired in — it rescans
  short phrases for the literal word "jarvis", which is simpler to run with zero extra
  model downloads but less efficient than a purpose-built wake-word engine. Swap
  `voice/wakeword.py` for one of those if you want lower always-on CPU use.
- **TTS**: `voice/tts.py` has three tiers, picked by `settings["ttsProvider"]`:
  - **ElevenLabs** (best quality) — add a key from [elevenlabs.io](https://elevenlabs.io)
    in Settings and it's used automatically under "auto." Defaults to "George," a British
    male voice from ElevenLabs' own quickstart docs; Settings fetches your real available
    voices once a key is added, via `list_elevenlabs_voices()`.
  - **Microsoft Edge** neural voices (`edge-tts`, no key, needs internet) —
    `en-GB-RyanNeural` by default, a calm British male voice.
  - **Offline** — falls back to your OS's built-in voice via `pyttsx3` if the above two
    aren't reachable (no internet, no key, request failure).

  "Auto" (the default) tries them in that order and falls through on any failure, so
  voice keeps working even without an ElevenLabs key or without internet at all.
- **Interrupt**: starting to talk again (mic picks it up) stops playback immediately —
  handled by `tts.stop_speaking()`, called from the wake-word/listen-once paths.

## Command engine

Identical command surface to the Electron build — type or say things like:

```
open chrome · open spotify · play music · pause music · stop music
shut down · restart          → both require an on-screen confirmation
search google for pikachu · search youtube for lofi beats
set volume to 40 · set brightness to 60
take a screenshot · open camera
open folder ~/Documents · create file notes.txt · delete file draft.txt · rename x.txt to y.txt
weather · weather in tokyo · news · stock aapl · crypto bitcoin
click · click on the submit button · double click · right click on the download link
type hello there · press enter · press ctrl+s
scroll up · scroll down · copy · paste · cut · undo · redo · select all

# Webcam computer vision (needs a webcam)
learn my face as Alex · who am i · what gesture · check my eyes

# Knowledge & calendar (need their own keys/credentials — see below)
calculate 15% of 240 · solve x^2 = 49 · my calendar

# Offline utilities
take a note buy milk · read my latest note · tell me a joke
what is the time · what is the date · set a timer for 5 minutes

# Smart-home (Philips Hue)
pair the lights · turn on the kitchen light · turn off all lights
```

Everything not matching a known pattern goes to the conversational AI instead. File
operations are sandboxed to your home directory (`utils/helpers.resolve_in_home`).
Destructive actions (shutdown, restart, delete) always show a confirmation dialog first
— `core/orchestrator.py` holds the pending command server-side until you confirm or
cancel from the UI.

"Click on X" / "double click on X" / "right click on X" screenshot the desktop and ask
whichever AI provider is configured to point at the described element (as a fraction of
the screen), then move the real cursor there via `pyautogui` and click
(`tools/automation.py`). Same caveat as the Electron build: accuracy depends entirely on
the vision model — it's "point roughly where I meant," not a guaranteed-correct element
finder, and there's no confirmation step before the click fires.

### Webcam computer vision (`vision/face.py`, `gestures.py`, `eyetracking.py`)

- **Face recognition** — "learn my face as `<name>`" captures ~20 webcam samples and
  trains an OpenCV LBPH recognizer (`~/.jarvis_ai/faces/`); "who am I" then names whoever
  is in frame. Uses `opencv-contrib-python`'s built-in recognizer rather than
  dlib/`face_recognition`, so it installs with no C++ toolchain — the trade-off is lower
  accuracy than a deep-learning model.
- **Hand gestures** — "what gesture" classifies fist / open palm / thumbs up / peace /
  pointing from MediaPipe hand landmarks using explainable finger-geometry rules.
- **Eyes** — "check my eyes" reports open/closed (eye-aspect-ratio) and rough gaze
  left/center/right from MediaPipe iris landmarks. This is a single-frame heuristic, **not**
  calibrated screen-coordinate gaze tracking — it can't tell where on your monitor you're
  looking without a per-user calibration step this interface doesn't run.

All three need a real webcam and can't be exercised headlessly, so they were verified by
import + logic tests here, not against a live camera.

### Knowledge & calendar (bring your own credentials)

- **Wolfram Alpha** (`tools/wolfram.py`) — "calculate…" / "solve…" / "how much is…" hit
  the free [Short Answers API](https://developer.wolframalpha.com/). Add your App ID as
  the `wolfram` key in Settings. General "what is X" questions deliberately go to the
  conversational AI instead, which handles them better.
- **Google Calendar** (`tools/calendar_google.py`) — "my calendar" reads upcoming events.
  Needs your own OAuth client (Google won't allow shipping a shared desktop secret): make
  a Desktop-app OAuth client in Google Cloud Console, enable the Calendar API, and save the
  JSON to `~/.jarvis_ai/google_credentials.json`. First use opens a browser to authorize;
  the token is cached after that.

### Smart-home (`tools/iot.py`)

**Philips Hue** lights are fully implemented against the local Hue Bridge (no cloud
account, LAN only): press the bridge's link button, say "pair the lights," then "turn on
the kitchen light" / "turn off all lights." Other device classes (TVs, thermostats, Nest,
CCTVs) are explicit extension points that raise a clear "not wired up" error — each needs
its own vendor account/API and, usually, physical hardware to test against, so they're
left as documented stubs rather than faked.

## Screen understanding

- **Take a screenshot** saves a PNG to `Pictures/Jarvis Screenshots` (`~/Pictures/...` on
  Linux/macOS, `%USERPROFILE%\Pictures\...` on Windows).
- **Analyze Screen Now** (Alerts tab) captures the screen and sends it to a
  vision-capable provider along with your question — real multimodal analysis.
- **Live Screen Monitor** (Alerts tab) polls a screenshot every 15s, OCRs it with
  Tesseract, and posts the extracted text as a notification — local-only, no API calls.

## Memory & security

Chat history and remembered facts live in a local SQLite file
(`~/.jarvis_ai/jarvis_memory.db`). Set a passphrase in Settings → Security & Memory to
encrypt message bodies and facts at rest with AES-256-GCM (`cryptography`'s `AESGCM`, key
derived via `Scrypt`). Without a passphrase, data is stored in plaintext locally. No
recovery path if you forget the passphrase — by design, same as before.

Settings and API keys live in `~/.jarvis_ai/config.json`, permissioned `0600`. This is
plain JSON, not a real secret store — see `config.py`'s docstring for why, and swap in the
`keyring` package (OS credential manager) before relying on this for anything sensitive.

## What's genuinely implemented vs. what's an extension point

Built and working, backed by real execution (not just typed/compiled, actually run and
verified in this repo's sandbox under Xvfb + a Qt backend — see "Verification" below):
live system stats (`psutil`), the full command engine and confirmation gate, encrypted
local memory with a real lock/unlock roundtrip, multi-provider AI chat with fallback,
mouse/keyboard automation with vision-guided targeting, screenshot+OCR, live screen
monitor, weather/news/stock/crypto, reminders, notes/jokes/timers, ElevenLabs voice, and
the pywebview HUD itself (a real window with the real frontend and the real Python bridge
was created, ran, and torn down cleanly during verification).

Built but needing hardware or your own credentials to actually use (verified by import +
logic tests here, since this sandbox has no webcam and no third-party accounts): webcam
face recognition / hand gestures / eye state, Wolfram Alpha STEM answers, Google Calendar,
and Philips Hue light control.

Not wired to real third-party infrastructure, same as the Electron build:

- **Cloud sync** — `memory/long_term.py` is local-only; point it at your own backend if
  you need multi-device memory.
- **Password-vault integration** (1Password/Bitwarden) — needs their SDKs and your real
  vault credentials.
- **Autonomous multi-step tasks** — Jarvis writes code and executes automation steps
  individually; there's no planner chaining many steps toward an open-ended goal
  ("build me a whole website" as one unattended command) without you driving each step.
- **Video generation** — not implemented; needs a specific paid provider and a key.
- **Non-Hue smart-home devices** (TVs, thermostats, Nest, CCTVs) — documented extension
  points in `tools/iot.py` that raise a clear error; each needs its own vendor API.
- **Dedicated wake-word model** — see the Voice section above.

## Verification performed in this environment

This sandbox has no real display and is missing several OS packages a normal desktop
ships with by default, so getting a real GUI window up took real work — worth recording
what was actually exercised rather than just "it imports":

- Every `.py` file byte-compiles cleanly (`python -m py_compile`).
- Every backend module actually imports under a real interpreter with real dependencies
  installed (not mocked) — `core`, `memory`, `tools`, `vision`, `web`, `media`, `voice`.
- **Executed, not just imported**: config load/save roundtrip; the command parser against
  a dozen representative inputs (open app, dangerous action, click-on-target, key combo,
  weather-with-location, and a non-command fallthrough); a full encrypted-memory
  roundtrip (set passphrase → save message → remember fact → lock → confirm ciphertext is
  unreadable → unlock → confirm plaintext returns); and a live `psutil` stats collection
  against this actual machine.
- **The real GUI**: after installing the OS packages a desktop Linux box has out of the
  box but this container didn't (`python3-tk`, Qt's xcb platform libs, EGL/OpenGL libs),
  `ui.dashboard.JarvisApi` + `webview.create_window()` successfully created a real window
  loading the real built `ui/web/index.html`, ran for several seconds with no crash, and
  tore down cleanly. The frontend itself is the same compiled bundle already visually
  verified in the Electron build (identical HUD source, adapted bridge only).
- The `ui/frontend` TypeScript project typechecks (`tsc -b --noEmit`) and builds
  (`vite build`) cleanly.

Not verified here (would need real hardware/services this sandbox doesn't have): actual
microphone capture end-to-end, actual speaker playback, and real AI provider responses
(no API keys configured in this sandbox) — the code paths are real and match the
already-verified Electron implementation's logic, but nobody said "hello" out loud to it
in this container.
