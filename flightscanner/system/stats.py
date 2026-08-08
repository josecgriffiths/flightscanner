"""System statistics scaffold -- not yet wired into a page.

Will eventually be populated using psutil, cached and refreshed at
roughly 1 Hz rather than sampled every render frame.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SystemStats:
    cpu_percent: float | None = None
    ram_percent: float | None = None
    cpu_temp_c: float | None = None
    uptime_s: float | None = None
