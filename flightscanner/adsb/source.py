"""AircraftSource interface.

The rest of the application depends only on this abstraction, never on a
concrete source, so the UI and geometry pipeline are identical whether
aircraft come from dump1090-fa or the simulator.
"""
from __future__ import annotations

from typing import Protocol

from flightscanner.adsb.models import Aircraft


class AircraftSource(Protocol):
    def get_aircraft(self) -> list[Aircraft]:
        """Return the current snapshot of known aircraft."""
        ...

    def status(self) -> str:
        """Short human-readable status, e.g. 'LIVE', 'DEMO', 'OFFLINE'."""
        ...
