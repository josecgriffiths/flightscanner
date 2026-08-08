"""Simulated ADS-B source for development on machines without a receiver.

Generates a population of fake aircraft around the receiver location and
moves them over time using their reported speed/track, via the same
great-circle maths the live pipeline will eventually use. Aircraft that
wander far outside the radar area are reseeded rather than deleted, so
the population size stays constant.
"""
from __future__ import annotations

import math
import random
import time

from flightscanner.adsb.geometry import EARTH_RADIUS_M, METRES_PER_NM
from flightscanner.adsb.models import Aircraft

DEMO_CALLSIGNS = [
    "BAW123", "EZY42A", "RYR81", "VIR25", "LOG52", "TOM7PK",
    "BAW45C", "EZY19K", "RYR22Q", "VIR9", "LOG3F", "SHT1A",
    "AFR22K", "DLH4B", "KLM88", "UAE9",
]

RESEED_RANGE_MULTIPLIER = 1.5  # reseed once an aircraft drifts this far past range


class SimulatorSource:
    """AircraftSource implementation producing moving, fake aircraft."""

    def __init__(
        self,
        receiver_lat: float,
        receiver_lon: float,
        count: int = 15,
        seed: int = 42,
        radar_range_nm: float = 50.0,
    ) -> None:
        self._receiver_lat = receiver_lat
        self._receiver_lon = receiver_lon
        self._radar_range_nm = radar_range_nm
        self._rng = random.Random(seed)
        self._last_update = time.monotonic()
        self._aircraft: list[_SimAircraft] = [
            self._spawn(i) for i in range(count)
        ]

    def get_aircraft(self) -> list[Aircraft]:
        now = time.monotonic()
        elapsed = now - self._last_update
        self._last_update = now

        result: list[Aircraft] = []
        for sim in self._aircraft:
            sim.advance(elapsed)
            if sim.distance_from_home_nm() > self._radar_range_nm * RESEED_RANGE_MULTIPLIER:
                self._reseed(sim)
            result.append(sim.to_aircraft())
        return result

    def status(self) -> str:
        return "DEMO"

    def _spawn(self, index: int) -> "_SimAircraft":
        callsign = self._rng.choice(DEMO_CALLSIGNS)
        icao = f"{self._rng.randrange(0, 0xFFFFFF):06x}"
        return _SimAircraft.random_near(
            self._receiver_lat,
            self._receiver_lon,
            self._radar_range_nm,
            icao,
            callsign,
            self._rng,
        )

    def _reseed(self, sim: "_SimAircraft") -> None:
        fresh = self._spawn(0)
        sim.icao = fresh.icao
        sim.callsign = fresh.callsign
        sim.lat = fresh.lat
        sim.lon = fresh.lon
        sim.altitude = fresh.altitude
        sim.ground_speed = fresh.ground_speed
        sim.track = fresh.track
        sim.vertical_rate = fresh.vertical_rate
        sim.home_lat = self._receiver_lat
        sim.home_lon = self._receiver_lon


class _SimAircraft:
    """Mutable simulated flight state, advanced by elapsed real time."""

    def __init__(
        self,
        icao: str,
        callsign: str,
        lat: float,
        lon: float,
        altitude: float,
        ground_speed: float,
        track: float,
        vertical_rate: float,
        home_lat: float,
        home_lon: float,
    ) -> None:
        self.icao = icao
        self.callsign = callsign
        self.lat = lat
        self.lon = lon
        self.altitude = altitude
        self.ground_speed = ground_speed
        self.track = track
        self.vertical_rate = vertical_rate
        self.home_lat = home_lat
        self.home_lon = home_lon

    @classmethod
    def random_near(
        cls,
        home_lat: float,
        home_lon: float,
        radar_range_nm: float,
        icao: str,
        callsign: str,
        rng: random.Random,
    ) -> "_SimAircraft":
        distance_nm = rng.uniform(radar_range_nm * 0.1, radar_range_nm * 0.9)
        bearing_deg = rng.uniform(0, 360)
        lat, lon = _offset_position(home_lat, home_lon, distance_nm, bearing_deg)
        return cls(
            icao=icao,
            callsign=callsign,
            lat=lat,
            lon=lon,
            altitude=rng.uniform(3000, 38000),
            ground_speed=rng.uniform(180, 480),
            track=rng.uniform(0, 360),
            vertical_rate=rng.choice([0, 0, 0, rng.uniform(-1800, 1800)]),
            home_lat=home_lat,
            home_lon=home_lon,
        )

    def advance(self, elapsed_seconds: float) -> None:
        if elapsed_seconds <= 0:
            return
        distance_nm = (self.ground_speed * elapsed_seconds) / 3600.0
        self.lat, self.lon = _offset_position(self.lat, self.lon, distance_nm, self.track)
        self.altitude = max(0.0, self.altitude + self.vertical_rate * (elapsed_seconds / 60.0))

    def distance_from_home_nm(self) -> float:
        from flightscanner.adsb.geometry import haversine_distance_nm

        return haversine_distance_nm(self.home_lat, self.home_lon, self.lat, self.lon)

    def to_aircraft(self) -> Aircraft:
        return Aircraft(
            icao=self.icao,
            callsign=self.callsign,
            latitude=self.lat,
            longitude=self.lon,
            altitude_baro=round(self.altitude),
            ground_speed=round(self.ground_speed, 1),
            track=round(self.track, 1),
            vertical_rate=round(self.vertical_rate),
            seen=0.0,
            seen_position=0.0,
        )


def _offset_position(
    lat: float, lon: float, distance_nm: float, bearing_deg: float
) -> tuple[float, float]:
    """Move (lat, lon) by distance_nm along bearing_deg on a spherical Earth."""
    angular_distance = (distance_nm * METRES_PER_NM) / EARTH_RADIUS_M
    bearing_rad = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)
