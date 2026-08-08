"""Logging configuration: console during development, rotating file always.

Log file location follows the XDG-ish convention:
    ~/.local/state/flightscanner/flightscanner.log
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "state" / "flightscanner"
LOG_FILE = LOG_DIR / "flightscanner.log"

MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def setup_logging(debug: bool = False) -> None:
    """Configure root logger with console + rotating file handlers."""
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s: %(message)s", "%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        root.warning("Could not create log file at %s; console logging only", LOG_FILE)
