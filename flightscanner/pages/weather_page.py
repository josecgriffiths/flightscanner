"""WEATHER page -- fetches current conditions for the receiver's
location via WeatherReader (Open-Meteo). Never required for radar
operation; fails silently and just shows an unavailable state if
offline or unconfigured.
"""
from __future__ import annotations

import pygame

from flightscanner.pages.receiver_page import draw_placeholder
from flightscanner.services.weather import WeatherReader
from flightscanner.ui import theme

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

    heading_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_HEADING)
    value_font = pygame.font.Font(theme.FONT_NAME, 60)
    label_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_NORMAL)
    small_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)

    cx, cy = theme.SCREEN_CENTER

    title_surf = heading_font.render("WEATHER", True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 130)))

    temp_surf = value_font.render(f"{reading.temperature_c:.0f}°C", True, theme.TEXT_PRIMARY)
    surface.blit(temp_surf, temp_surf.get_rect(center=(cx, cy - 40)))

    condition_surf = label_font.render(reading.condition, True, theme.ACCENT)
    surface.blit(condition_surf, condition_surf.get_rect(center=(cx, cy + 30)))

    wind_surf = small_font.render(f"WIND {reading.wind_speed_kt:.0f} KT", True, theme.TEXT_MUTED)
    surface.blit(wind_surf, wind_surf.get_rect(center=(cx, cy + 70)))
