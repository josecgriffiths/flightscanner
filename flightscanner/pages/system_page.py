"""SYSTEM STATUS page -- CPU/RAM/temperature/uptime via psutil.

Stats are sampled at most once per second by a module-level
SystemStatsReader, since psutil.cpu_percent() needs a real interval
between calls and there's no reason to hit /sys for temperature every
render frame.
"""
from __future__ import annotations

import pygame

from flightscanner.system.stats import SystemStatsReader
from flightscanner.ui import theme, widgets

_reader = SystemStatsReader()

GAUGE_RADIUS = 56
GAUGE_SPACING = 148
TEMP_GAUGE_MAX_C = 90.0  # full scale for the temperature ring


def draw(surface: pygame.Surface) -> None:
    stats = _reader.read()

    widgets.draw_page_title(surface, "SYSTEM")
    cx, cy = theme.SCREEN_CENTER

    gauges = [
        ("CPU", _format_percent(stats.cpu_percent), _fraction(stats.cpu_percent, 100),
         _warn_color(stats.cpu_percent, 85)),
        ("RAM", _format_percent(stats.ram_percent), _fraction(stats.ram_percent, 100),
         _warn_color(stats.ram_percent, 90)),
        ("TEMP", _format_temp(stats.cpu_temp_c), _fraction(stats.cpu_temp_c, TEMP_GAUGE_MAX_C),
         _warn_color(stats.cpu_temp_c, 80)),
    ]
    for i, (label, value, fraction, color) in enumerate(gauges):
        center = (cx + (i - 1) * GAUGE_SPACING, cy - 20)
        widgets.draw_ring_gauge(surface, center, GAUGE_RADIUS, fraction, color, label, value)

    uptime_rect = pygame.Rect(0, 0, 240, 74)
    uptime_rect.center = (cx, cy + 120)
    widgets.draw_stat_tile(surface, uptime_rect, "UPTIME", _format_uptime(stats.uptime_s))


def _fraction(value: float | None, full_scale: float) -> float | None:
    return None if value is None else value / full_scale


def _warn_color(value: float | None, threshold: float) -> tuple[int, int, int]:
    if value is not None and value >= threshold:
        return theme.WARNING
    return theme.ACCENT


def _format_percent(value: float | None) -> str:
    return f"{value:.0f}%" if value is not None else "N/A"


def _format_temp(value: float | None) -> str:
    return f"{value:.0f}°C" if value is not None else "N/A"


def _format_uptime(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    total_minutes = int(seconds // 60)
    days, rem_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem_minutes, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"
