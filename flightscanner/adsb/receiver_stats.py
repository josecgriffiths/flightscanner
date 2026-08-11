"""Reads dump1090-fa's stats.json for receiver health -- decoupled from
the aircraft.json reading in dump1090.py so the RECEIVER STATUS page
never touches the radar's data path.

Same resilience posture as Dump1090Source: a missing file, a torn
read, or an unexpected shape are all logged and treated as a failed
read rather than raised, since stats.json is rewritten periodically by
dump1090-fa and can be caught mid-write.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

STALE_GRACE_SECONDS = 15.0


@dataclass
class ReceiverStats:
    messages_total: int | None = None
    messages_per_second: float | None = None
    signal_dbfs: float | None = None
    noise_dbfs: float | None = None
    strong_signals: int | None = None
    position_count: int | None = None


class ReceiverStatsReader:
    def __init__(self, path: str | Path, stale_grace_seconds: float = STALE_GRACE_SECONDS) -> None:
        self._path = Path(path)
        self._stale_grace_seconds = stale_grace_seconds
        self._last_good: ReceiverStats | None = None
        self._last_good_time: float | None = None

    def read(self) -> ReceiverStats | None:
        stats = self._try_read()
        if stats is not None:
            self._last_good = stats
            self._last_good_time = time.monotonic()
            return stats

        if self._last_good_time is not None:
            age = time.monotonic() - self._last_good_time
            if age <= self._stale_grace_seconds:
                return self._last_good

        return None

    def _try_read(self) -> ReceiverStats | None:
        try:
            raw_text = self._path.read_text()
        except OSError:
            return None

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.debug("Failed to parse stats.json (likely mid-write)")
            return None

        if not isinstance(payload, dict):
            return None

        last_minute = payload.get("last1min")
        total = payload.get("total")
        if not isinstance(last_minute, dict) or not isinstance(total, dict):
            return None

        local = last_minute.get("local") if isinstance(last_minute.get("local"), dict) else {}
        messages = last_minute.get("messages")

        return ReceiverStats(
            messages_total=_as_int(total.get("messages")),
            messages_per_second=(messages / 60.0) if isinstance(messages, (int, float)) else None,
            signal_dbfs=_as_float(local.get("signal")),
            noise_dbfs=_as_float(local.get("noise")),
            strong_signals=_as_int(local.get("strong_signals")),
            position_count=_as_int(last_minute.get("cpr", {}).get("global_ok") if isinstance(last_minute.get("cpr"), dict) else None),
        )


def _as_int(value) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _as_float(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None
