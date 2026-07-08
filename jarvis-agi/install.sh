#!/usr/bin/env bash
# JARVIS-AGI one-command setup for a ChromeOS Chromebook (Crostini / Debian Linux).
# Safe to run again any time (e.g. after `git pull`). It installs system packages, builds a
# Python environment, installs the app, and helps you save your free Groq key.

set -u  # (no `set -e`: we handle failures ourselves so one hiccup never aborts the whole run)

# Always run from the folder this script lives in.
cd "$(dirname "$0")" || exit 1

say()  { printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[1;32m✓ %s\033[0m\n' "$1"; }
warn() { printf '  \033[1;33m! %s\033[0m\n' "$1"; }

echo "=================================================="
echo "   J.A.R.V.I.S.  —  setting everything up"
echo "=================================================="

# ---------------------------------------------------------------------------
# 1. System packages (WebKit for the window, mpg123 for the voice, mic bits).
# ---------------------------------------------------------------------------
if command -v apt >/dev/null 2>&1; then
    say "Installing system packages (you may be asked for your password)…"
    sudo apt update -y
    # Core packages Jarvis needs to show its window and speak:
    if sudo apt install -y python3 python3-venv python3-pip git \
        python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 mpg123; then
        ok "Core packages installed (window + voice)."
    else
        warn "Some core packages failed — Jarvis may not open its window. See errors above."
    fi
    # Microphone packages are OPTIONAL (only needed for 'Hi Jarvis' voice input).
    say "Installing optional microphone support…"
    if sudo apt install -y python3-pyaudio flac; then
        ok "Microphone support installed."
    else
        warn "Mic packages didn't install — that's OK. Chat + voice replies still work; you"
        warn "just won't be able to talk to Jarvis. You can type instead."
    fi
else
    warn "This doesn't look like a Debian/Chromebook system (no 'apt')."
    warn "Install manually: python3, python3-venv, git, GTK+WebKit for pywebview, and mpg123."
fi

# ---------------------------------------------------------------------------
# 2. Python virtual environment (with system GTK visible to it).
# ---------------------------------------------------------------------------
say "Building the Python environment…"
if [ ! -d ".venv" ]; then
    # --system-site-packages lets the venv see the apt-installed GTK/WebKit bindings.
    python3 -m venv .venv --system-site-packages || {
        warn "Could not create the virtual environment. Is python3-venv installed?"; exit 1;
    }
    ok "Created .venv"
else
    ok "Reusing existing .venv"
fi

# ---------------------------------------------------------------------------
# 3. Python dependencies.
# ---------------------------------------------------------------------------
say "Installing Python packages…"
./.venv/bin/pip install --upgrade pip >/dev/null 2>&1
if ./.venv/bin/pip install -r requirements.txt; then
    ok "Python packages installed."
else
    warn "Some Python packages failed to install — check the errors above."
fi

# ---------------------------------------------------------------------------
# 4. API key — Jarvis needs a free Groq key to think.
# ---------------------------------------------------------------------------
CONFIG="$HOME/.jarvis_agi/config.json"
if grep -q '"groq"[[:space:]]*:[[:space:]]*"[^"]' "$CONFIG" 2>/dev/null; then
    ok "A Groq key is already saved."
else
    say "One last thing: Jarvis needs a FREE Groq key to think."
    echo "  1. Open  https://console.groq.com/keys  in Chrome"
    echo "  2. Sign in (free, no card) and click 'Create API Key'"
    echo "  3. Copy the key (it starts with gsk_)"
    printf "\n  Paste your Groq key here now (or press Enter to skip and do it later): "
    read -r GROQ_KEY
    if [ -n "${GROQ_KEY:-}" ]; then
        ./.venv/bin/python set_key.py groq "$GROQ_KEY"
    else
        warn "Skipped. When ready:  python3 set_key.py groq gsk_YOURKEY"
    fi
fi

# ---------------------------------------------------------------------------
# Done.
# ---------------------------------------------------------------------------
echo ""
echo "=================================================="
ok "Setup complete!"
echo "=================================================="
echo ""
echo "  Start Jarvis any time with:   ./start.sh"
echo ""
