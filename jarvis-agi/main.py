"""JARVIS-AGI entry point: initialize local memory, then launch the pywebview HUD."""

from CORE import memory
from UI import dashboard


def main() -> None:
    print("[jarvis-agi] Starting J.A.R.V.I.S. ...", flush=True)
    memory.init_db()
    dashboard.run()


if __name__ == "__main__":
    main()
