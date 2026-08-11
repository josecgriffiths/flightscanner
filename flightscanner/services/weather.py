"""Weather lookup via Open-Meteo's free, key-less forecast API.

Never required for the radar to function -- any failure (offline, DNS,
timeout, malformed response) is caught and logged at debug level, and
callers simply keep showing the last known-good reading (or nothing).
Refreshed at most once per `refresh_minutes` since this is a blocking
HTTP call and the app has no background thread for it; a small hitch
every several minutes is an acceptable tradeoff for staying simple.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 5.0

# WMO weather interpretation codes -> short display text.
WEATHER_CODES: dict[int, str] = {
    0: "CLEAR SKY", 1: "MOSTLY CLEAR", 2: "PARTLY CLOUDY", 3: "OVERCAST",
    45: "FOG", 48: "FOG",
    51: "LIGHT DRIZZLE", 53: "DRIZZLE", 55: "DENSE DRIZZLE",
    61: "LIGHT RAIN", 63: "RAIN", 65: "HEAVY RAIN",
    71: "LIGHT SNOW", 73: "SNOW", 75: "HEAVY SNOW",
    80: "RAIN SHOWERS", 81: "RAIN SHOWERS", 82: "VIOLENT SHOWERS",
    95: "THUNDERSTORM", 96: "THUNDERSTORM", 99: "THUNDERSTORM",
}


@dataclass
class WeatherReading:
    temperature_c: float
    wind_speed_kt: float
    condition: str


class WeatherReader:
    def __init__(self, latitude: float, longitude: float, refresh_minutes: float) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._refresh_interval = max(refresh_minutes, 1.0) * 60.0
        self._cached: WeatherReading | None = None
        self._next_fetch = 0.0

    def read(self, now: float | None = None) -> WeatherReading | None:
        now = now if now is not None else time.monotonic()
        if now < self._next_fetch:
            return self._cached

        self._next_fetch = now + self._refresh_interval
        fetched = self._fetch()
        if fetched is not None:
            self._cached = fetched
        return self._cached

    def _fetch(self) -> WeatherReading | None:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self._latitude}&longitude={self._longitude}"
            "&current=temperature_2m,wind_speed_10m,weather_code"
            "&wind_speed_unit=kn"
        )
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_S) as response:
                payload = json.loads(response.read())
        except Exception:
            logger.debug("Weather fetch failed", exc_info=True)
            return None

        current = payload.get("current")
        if not isinstance(current, dict):
            return None

        try:
            temp = float(current["temperature_2m"])
            wind = float(current["wind_speed_10m"])
            code = int(current["weather_code"])
        except (KeyError, TypeError, ValueError):
            return None

        return WeatherReading(
            temperature_c=temp,
            wind_speed_kt=wind,
            condition=WEATHER_CODES.get(code, "UNKNOWN"),
        )
