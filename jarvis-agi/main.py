"""JARVIS-AGI entry point: initialize local memory, load plugins, then launch the HUD."""

from CORE import memory, plugins
from UI import dashboard


def main() -> None:
    print("[jarvis-agi] Starting J.A.R.V.I.S. 2.2 ...", flush=True)
    memory.init_db()
    plugins.load_plugins()
    dashboard.run()


if __name__ == "__main__":
    main()
