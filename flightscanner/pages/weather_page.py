"""WEATHER page -- fetches current conditions for the receiver's
location via WeatherReader (Open-Meteo). Never required for radar
operation; fails silently and just shows an unavailable state if
offline or unconfigured.
"""
from __future__ import annotations

import pygame

from flightscanner.pages.receiver_page import draw_placeholder
from flightscanner.services.weather import WeatherReader
from flightscanner.ui import gfx, theme, widgets

_reader: WeatherReader | None = None
_enabled = True


def configure(latitude: float | None, longitude: float | None, enabled: bool, refresh_minutes: float) -> None:
    global _reader, _enabled
    _enabled = enabled
    if enabled and latitude is not None and longitude is not None:
        _reader = WeatherReader(latitude, longitude, refresh_minutes)
    else:
        _reader = None


def draw(surface: pygame.Surface) -> None:
    if not _enabled or _reader is None:
        draw_placeholder(surface, "WEATHER")
        return

    reading = _reader.read()
    if reading is None:
        draw_placeholder(surface, "WEATHER")
        return

    widgets.draw_page_title(surface, "WEATHER")
    cx, cy = theme.SCREEN_CENTER

    temp = gfx.blit_text(
        surface, f"{reading.temperature_c:.0f}°", theme.FONT_SIZE_DISPLAY, theme.TEXT_PRIMARY,
        "light", center=(cx + 12, cy - 50),  # nudge right: the ° makes it look off-centre
    )
    gfx.blit_text(
        surface, reading.condition.upper(), theme.FONT_SIZE_SMALL, theme.ACCENT, "semibold",
        theme.TRACKING_LABEL, center=(cx, temp.bottom + 14),
    )

    wind_rect = pygame.Rect(0, 0, 220, 74)
    wind_rect.center = (cx, cy + 120)
    widgets.draw_stat_tile(surface, wind_rect, "WIND", f"{reading.wind_speed_kt:.0f} KT")
