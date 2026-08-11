"""System statistics: CPU/RAM/temperature/uptime via psutil.

Sampled at most once per second by SystemStatsReader.read() -- callers
poll every frame, but psutil.cpu_percent() needs a real interval between
calls to be meaningful, and there is no need to hit the filesystem for
temperature every frame either.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import psutil

SAMPLE_INTERVAL_S = 1.0
THERMAL_ZONE_PATH = Path("/sys/class/thermal/thermal_zone0/temp")


@dataclass
class SystemStats:
    cpu_percent: float | None = None
    ram_percent: float | None = None
    cpu_temp_c: float | None = None
    uptime_s: float | None = None


class SystemStatsReader:
    """Caches SystemStats, refreshing at most once per SAMPLE_INTERVAL_S."""

    def __init__(self) -> None:
        self._cached = SystemStats()
        self._next_sample = 0.0

    def read(self, now: float | None = None) -> SystemStats:
        now = now if now is not None else time.monotonic()
        if now < self._next_sample:
            return self._cached

        self._next_sample = now + SAMPLE_INTERVAL_S
        self._cached = SystemStats(
            cpu_percent=_safe(psutil.cpu_percent),
            ram_percent=_safe(lambda: psutil.virtual_memory().percent),
            cpu_temp_c=_read_cpu_temp(),
            uptime_s=_safe(lambda: time.time() - psutil.boot_time()),
        )
        return self._cached


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def _read_cpu_temp() -> float | None:
    try:
        raw = THERMAL_ZONE_PATH.read_text().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError):
        return None
