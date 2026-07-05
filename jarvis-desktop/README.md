# J.A.R.V.I.S. Desktop

A holographic-HUD desktop AI assistant, built with Electron + React + TypeScript.
Black/cyan/orange glassmorphic interface, live system monitoring, multi-provider AI
chat with local encrypted memory, browser-based voice (wake word + British TTS), and
a natural-language command engine for controlling the desktop.

## Architecture

```
jarvis-desktop/
  electron/            Main process (Node) — the only place with OS/API-key access
    main.ts            Window creation, security policy (external nav blocked)
    preload.ts          contextBridge surface exposed to the renderer as window.jarvis
    store.ts            Local JSON settings/API-key persistence
    services/
      ai/               Anthropic / OpenAI / Gemini / Ollama adapters + fallback router
      system/           Stats polling, command parser + dispatcher, web data (weather/news/stocks/crypto)
      memory/           better-sqlite3 store + AES-256-GCM field encryption
      screen/           Screenshot capture + Tesseract OCR
    ipc/                One file per IPC surface, registered from main.ts
  src/                  Renderer (React) — the HUD, no direct Node/OS access
    components/hud      Radar/orb centerpiece, top status bar
    components/panels    Left (system vitals), right (chat/thoughts/alerts/schedule), bottom (terminal)
    lib/voice           Web Speech API wake-word engine + TTS voice selection
    lib/commands        Renderer-side command dispatch (parse → confirm-if-dangerous → execute)
    state/store.ts       zustand store
  shared/types.ts        Type contracts shared by main + renderer (IPC channel names live here)
```

All AI provider calls and API keys stay in the main process; the renderer never sees a
raw key — it only talks to `window.jarvis.*`, a typed IPC bridge installed via
`contextBridge` with `nodeIntegration: false` / `contextIsolation: true`. Outbound
in-app navigation is blocked and forced to the OS browser.

## Setup

Requires Node.js ≥ 20 (Electron 33's floor).

```bash
npm install
npm run dev          # Vite dev server for the HUD, hot reload
npm run dev:electron # in a second terminal — compiles main/preload and launches Electron pointed at the dev server
```

Production build:

```bash
npm run build        # renderer (vite build) + main process (tsc)
npm start             # build + launch
npm run package       # electron-builder — produces a dmg/nsis/AppImage in release/
```

`better-sqlite3` ships a native binding. If you see a Node ABI mismatch when running
under packaged Electron, run `npx electron-rebuild` once after `npm install`.

## Configure API keys and providers

Open **Settings** (gear icon, bottom-right of the terminal bar) and enter keys for
whichever providers you use:

- **Anthropic** — Claude, used for the main assistant persona by default
- **OpenAI** — GPT, also used for screen/image analysis (vision)
- **Google Gemini**
- **Ollama** — no key needed; point "Ollama base URL" at a local `ollama serve` (default `http://127.0.0.1:11434`)
- **OpenWeather** / **NewsAPI** — optional, unlock the Weather and News widgets

Drag providers in "AI Model Fallback Order" to set which one is tried first; if a
provider errors or isn't configured, the router automatically falls through to the
next one. Stock and crypto quotes use keyless public endpoints (Stooq, CoinGecko) and
need no setup.

## Voice

Voice uses the browser **Web Speech API** built into Electron's Chromium — no external
speech service is wired up, so there's no extra key to configure, but recognition
quality depends on Chromium's built-in engine and an internet connection (Chromium's
on-device recognizer is limited). Say **"Jarvis"** to wake it, or click the mic button
to talk without the wake word.

Text-to-speech has two tiers, picked by Settings → Voice → "Voice engine":

- **ElevenLabs** (best quality) — add an API key from [elevenlabs.io](https://elevenlabs.io)
  in Settings → API Keys and it becomes available. Defaults to "George," a British male
  voice from ElevenLabs' own quickstart docs; once a key is added, Settings fetches your
  actual available voices so you can pick a different one. The key never leaves the main
  process — the renderer only asks main to synthesize and gets back audio bytes to play,
  the same boundary every other API key in this app respects.
- **Browser voice** (free, no key) — picks the best installed `en-GB` voice it can find
  (preferring names like "Google UK English Male" or "Daniel"), selectable in Settings.
  If your OS has no English (UK) voice pack installed, install one.

"Auto" (the default) tries ElevenLabs first if a key is configured and falls back to the
browser voice on any failure (no key, network error, bad voice ID) — so voice keeps
working even if ElevenLabs is temporarily unreachable. Speaking is interrupted
automatically the moment the mic picks up your voice again, regardless of which engine
is talking.

## Command engine

Type or say things like:

```
open chrome · open spotify · play music · pause music · stop music
shut down · restart          → both require an on-screen confirmation
search google for pikachu · search youtube for lofi beats
set volume to 40 · set brightness to 60
take a screenshot · open camera
open folder ~/Documents · create file notes.txt · delete file draft.txt · rename x.txt to y.txt
weather · weather in tokyo · news · stock aapl · crypto bitcoin
```

Anything that doesn't match a known pattern is handed to the conversational AI instead.
File operations are sandboxed to your home directory; destructive actions (shutdown,
restart, delete) always show a confirmation dialog before running.

## Computer control

Jarvis has real mouse/keyboard hands via [`@nut-tree-fork/nut-js`](https://github.com/nut-tree/nut-js)
(`electron/services/system/automation.ts`). Voice/text commands:

```
click · click on the submit button · double click · double click on the search box
right click · right click on the download link
type hello there · press enter · press ctrl+s · press cmd+shift+4
scroll up · scroll down
copy · paste · cut · undo · redo · select all
```

"Click on X" / "double click on X" / "right click on X" work by taking a screenshot,
asking whichever vision-capable AI provider is configured to point at the described
element (as a fraction of the screen, so it's resolution-independent), then moving the
real cursor there and clicking (`electron/services/ai/vision.ts`). This is genuinely
useful but **not infallible** — accuracy depends entirely on the vision model's ability
to locate small or ambiguous UI elements in a screenshot; it will occasionally click the
wrong thing. Treat it as "point roughly where I meant," not a guaranteed-correct
element finder — there's no confirmation step before the click happens today, so keep
an eye on the screen while testing this, especially for the first few uses.

**Before this works, your OS needs to grant input-control permission to the app**:

- **macOS**: System Settings → Privacy & Security → Accessibility (for control) and
  Screen Recording (for screenshots/vision) — add the packaged app, or Electron/Terminal
  in dev.
- **Windows**: works out of the box for most apps; some elevated/admin windows will
  refuse synthetic input from a non-elevated process (run Jarvis as admin if you need to
  control those).
- **Linux**: `nut.js`'s native binding targets X11. Under Wayland you'll likely need
  `xwayland` or to run the session under Xorg for mouse/keyboard control to work.

`@nut-tree-fork/nut-js` ships prebuilt native bindings per OS/arch; if you hit a Node
ABI mismatch after packaging, the same `npx electron-rebuild` mentioned above for
`better-sqlite3` covers this too.

## Screen understanding

- **Take a screenshot** saves a PNG to `Pictures/Jarvis Screenshots`.
- **Analyze Screen Now** (Alerts tab) captures the screen and sends it to a
  vision-capable provider (Anthropic/OpenAI/Gemini) along with your question, for real
  multimodal analysis of what's on screen.
- **Live Screen Monitor** (Alerts tab) polls a screenshot every 15s, runs it through
  Tesseract OCR, and posts the extracted text as a notification — a lightweight,
  local-only way to keep a running text log of what's visible without spending API
  calls on every tick.

## Memory & security

Chat history and remembered facts live in a local SQLite file
(`<userData>/jarvis-memory.db`). Set a passphrase in **Settings → Security & Memory**
to encrypt message bodies and facts at rest with AES-256-GCM (key derived via scrypt).
Without a passphrase, data is stored in plaintext locally — set one before relying on
this for anything sensitive. There's no recovery path if you forget the passphrase, by
design.

## What's genuinely implemented vs. what's an extension point

Built and working: HUD UI with radar/rings/sweep/glassmorphism, live system stats,
multi-provider streaming chat with fallback, encrypted local memory, wake-word +
British TTS voice with interrupt, the command engine above, screenshot+OCR, live
screen monitor, vision-based screen analysis, weather/news/stock/crypto, reminders,
notifications, real mouse/keyboard automation with vision-guided "click on X" targeting,
and a confirmation gate on destructive actions.

Deliberately **not** wired to real third-party infrastructure in this build — the
architecture leaves a clear seam to add each of these, but none of them talk to a live
external account out of the box:

- **Cloud sync** — no backend exists to sync to; `memory/db.ts` is local-only. Point it
  at your own sync service (e.g. Supabase/Postgres) if you need multi-device memory.
- **Password-vault integration** (1Password/Bitwarden) — would need their respective
  SDKs and your real vault credentials; not something to fake.
- **Autonomous multi-step tasks** ("build me a website" as one command that scaffolds,
  writes, and serves a whole project unattended) — Jarvis can write code and create
  files/run automation steps individually, but there's no planner chaining many steps
  toward an open-ended goal without you driving each step.
- **Video generation** — not implemented; would need a specific paid provider (e.g.
  Runway/Sora-style API) and a key for it.
- **Calendar sync** — `calendar:list` returns an empty list; wire up CalDAV/Google
  Calendar OAuth to make it live.
- **Volume/brightness on Windows** use a keystroke-simulation fallback (no native CLI
  shipped by Windows); Linux volume/brightness need `amixer`/`pactl`/`brightnessctl`
  installed, which most desktop distros already have.

## Verification performed in this environment

This sandbox has no display server and no network path to Electron's own binary CDN
(blocked at the proxy), so the packaged app itself could not be launched and
visually verified here. What *was* verified:

- `npx tsc -b --noEmit` — renderer typechecks clean
- `npx tsc -p electron/tsconfig.json --noEmit` — main process typechecks clean
- `npx vite build` — renderer bundles successfully
- `npx tsc -p electron/tsconfig.json` — main process compiles to `dist-electron/`
- `better-sqlite3` and `@nut-tree-fork/nut-js`'s native bindings both built successfully during `npm install`

Run `npm run dev` + `npm run dev:electron` on a real desktop to see it live.
