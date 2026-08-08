"""The Aircraft data model shared by every data source and by the UI.

The UI must never see raw dump1090 dictionaries or raw simulator state --
everything is normalised into an Aircraft instance first. Almost every
field is optional because dump1090 does not guarantee any particular
field is present for a given aircraft.
"""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Aircraft:
    icao: str  # lowercase hex address, e.g. "406abc" -- primary identity

    callsign: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_baro: float | int | str | None = None  # may be "ground"
    altitude_geom: float | None = None
    ground_speed: float | None = None
    track: float | None = None
    vertical_rate: float | None = None
    squawk: str | None = None
    rssi: float | None = None
    category: str | None = None
    seen: float | None = None  # seconds since last message
    seen_position: float | None = None  # seconds since last position update
    emergency: str | None = None

    # --- identity / display helpers ---------------------------------

    def display_callsign(self) -> str:
        """Trimmed callsign, falling back to the ICAO address."""
        if self.callsign:
            trimmed = self.callsign.strip()
            if trimmed:
                return trimmed
        return self.icao.upper()

    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def is_ground(self) -> bool:
        return isinstance(self.altitude_baro, str) and self.altitude_baro == "ground"

    def is_stale(self, threshold_seconds: float = 30.0) -> bool:
        return self.seen is not None and self.seen > threshold_seconds

    # --- formatted display values ------------------------------------

    def display_altitude(self) -> str | None:
        if self.is_ground():
            return "GROUND"
        alt = self.altitude_baro if self.altitude_baro is not None else self.altitude_geom
        if alt is None:
            return None
        try:
            return f"{int(alt):,} FT"
        except (TypeError, ValueError):
            return None

    def display_speed(self) -> str | None:
        if self.ground_speed is None:
            return None
        return f"{round(self.ground_speed)} KT"

    def display_track(self) -> str | None:
        if self.track is None:
            return None
        return f"{round(self.track) % 360}°"

    def display_vertical_rate(self) -> str | None:
        if self.vertical_rate is None:
            return None
        sign = "+" if self.vertical_rate >= 0 else ""
        return f"{sign}{round(self.vertical_rate)} FT/MIN"


def normalise_callsign(raw: str | None) -> str | None:
    """Trim whitespace from a raw dump1090 flight field; empty -> None."""
    if raw is None:
        return None
    trimmed = raw.strip()
    return trimmed or None


def aircraft_from_dump1090(entry: dict) -> Aircraft | None:
    """Build an Aircraft from one element of dump1090's aircraft.json list.

    Returns None if the entry has no usable ICAO address ("hex" field),
    since that is the only field we treat as mandatory.
    """
    icao = entry.get("hex")
    if not icao:
        return None

    return Aircraft(
        icao=str(icao).lower(),
        callsign=normalise_callsign(entry.get("flight")),
        latitude=entry.get("lat"),
        longitude=entry.get("lon"),
        altitude_baro=entry.get("alt_baro"),
        altitude_geom=entry.get("alt_geom"),
        ground_speed=entry.get("gs"),
        track=entry.get("track"),
        vertical_rate=entry.get("baro_rate", entry.get("geom_rate")),
        squawk=entry.get("squawk"),
        rssi=entry.get("rssi"),
        category=entry.get("category"),
        seen=entry.get("seen"),
        seen_position=entry.get("seen_pos"),
        emergency=entry.get("emergency"),
    )


def now_epoch() -> float:
    return time.time()
