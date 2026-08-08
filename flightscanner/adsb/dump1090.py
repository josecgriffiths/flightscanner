"""Live AircraftSource reading dump1090-fa's aircraft.json.

dump1090-fa rewrites this file roughly twice a second. Reads can race a
rewrite in progress, the file can briefly not exist, and its shape is
never guaranteed beyond "some JSON". None of that may crash the UI: on
any failure we log it and keep serving the last known-good snapshot for
a short grace period before reporting OFFLINE.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from flightscanner.adsb.models import Aircraft, aircraft_from_dump1090

logger = logging.getLogger(__name__)

# How long to keep serving a stale-but-valid snapshot after a read failure
# before treating the source as genuinely offline.
STALE_GRACE_SECONDS = 10.0


class Dump1090Source:
    """AircraftSource reading a dump1090-fa aircraft.json file."""

    def __init__(self, path: str | Path, stale_grace_seconds: float = STALE_GRACE_SECONDS) -> None:
        self._path = Path(path)
        self._stale_grace_seconds = stale_grace_seconds
        self._last_good_aircraft: list[Aircraft] = []
        self._last_good_time: float | None = None

    def get_aircraft(self) -> list[Aircraft]:
        aircraft = self._try_read()
        if aircraft is not None:
            self._last_good_aircraft = aircraft
            self._last_good_time = time.monotonic()
            return aircraft

        # Read failed -- retain the last valid snapshot briefly rather
        # than immediately clearing everything, since dump1090 rewrites
        # the file frequently and a single failed read is not unusual.
        if self._last_good_time is not None:
            age = time.monotonic() - self._last_good_time
            if age <= self._stale_grace_seconds:
                return self._last_good_aircraft

        return []

    def status(self) -> str:
        if self._last_good_time is None:
            return "OFFLINE"
        age = time.monotonic() - self._last_good_time
        return "LIVE" if age <= self._stale_grace_seconds else "OFFLINE"

    def _try_read(self) -> list[Aircraft] | None:
        try:
            raw_text = self._path.read_text()
        except FileNotFoundError:
            logger.warning("aircraft.json not found at %s", self._path)
            return None
        except OSError:
            logger.exception("Failed to read %s", self._path)
            return None

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            # dump1090 rewrites this file frequently; a torn read is
            # expected occasionally and not worth more than a debug log.
            logger.debug("Failed to parse aircraft.json (likely mid-write)")
            return None

        if not isinstance(payload, dict):
            logger.warning("aircraft.json root was not an object")
            return None

        entries = payload.get("aircraft")
        if not isinstance(entries, list):
            logger.warning("aircraft.json missing/invalid 'aircraft' list")
            return None

        aircraft: list[Aircraft] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            try:
                parsed = aircraft_from_dump1090(entry)
            except Exception:
                logger.exception("Failed to parse one aircraft entry; skipping it")
                continue
            if parsed is not None:
                aircraft.append(parsed)

        return aircraft
