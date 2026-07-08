#!/usr/bin/env bash
# Launch J.A.R.V.I.S. Run ./install.sh first if you haven't.

cd "$(dirname "$0")" || exit 1

if [ ! -x ".venv/bin/python" ]; then
    echo "Jarvis isn't set up yet. Run this first:"
    echo "    ./install.sh"
    exit 1
fi

exec ./.venv/bin/python main.py
