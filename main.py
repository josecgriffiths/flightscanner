#!/usr/bin/env python3
"""FLIGHTSCANNER entry point.

Examples:
    python main.py --demo
    python main.py --demo --scenario busy
    python main.py --live --fullscreen
"""
from __future__ import annotations

import argparse
import sys

from flightscanner.app import App
from flightscanner.config import default_config_path, load_config
from flightscanner.logging_setup import setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FLIGHTSCANNER ADS-B radar")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--demo", action="store_true", help="Run with simulated aircraft")
    mode_group.add_argument("--live", action="store_true", help="Run with live dump1090-fa data")

    parser.add_argument("--fullscreen", action="store_true", help="Launch fullscreen")
    parser.add_argument("--config", type=str, default=None, help="Path to config.toml")
    parser.add_argument(
        "--scenario", type=str, default=None, choices=["normal", "busy", "sparse"],
        help="Demo scenario preset (demo mode only)",
    )
    parser.add_argument("--debug", action="store_true", help="Start with debug overlay enabled")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(debug=args.debug)

    config_path = args.config or default_config_path()
    config = load_config(config_path)

    mode = "demo" if args.demo else "live"

    if mode == "live" and (config.receiver.latitude is None or config.receiver.longitude is None):
        print(
            "ERROR: --live requires receiver.latitude/longitude in config.toml "
            "(copy config.example.toml and edit it).",
            file=sys.stderr,
        )
        return 1

    app = App(
        config=config,
        mode=mode,
        fullscreen=args.fullscreen or config.display.fullscreen,
        debug=args.debug,
        scenario=args.scenario,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
