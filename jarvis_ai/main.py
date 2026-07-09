"""Entry point: initialize logging + persistent memory, then hand off to the pywebview HUD."""

from core.logger import get_logger
from memory.long_term import init_db
from ui import dashboard


def main() -> None:
    logger = get_logger("main")
    logger.info("Starting J.A.R.V.I.S....")
    init_db()
    dashboard.run()


if __name__ == "__main__":
    main()
