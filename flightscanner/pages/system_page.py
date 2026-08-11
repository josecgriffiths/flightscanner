"""SYSTEM STATUS page -- CPU/RAM/temperature/uptime via psutil.

Stats are sampled at most once per second by a module-level
SystemStatsReader, since psutil.cpu_percent() needs a real interval
between calls and there's no reason to hit /sys for temperature every
render frame.
"""
from __future__ import annotations

import pygame

from flightscanner.system.stats import SystemStatsReader
from flightscanner.ui import theme

_reader = SystemStatsReader()

ROW_SPACING = 44


def draw(surface: pygame.Surface) -> None:
    stats = _reader.read()

    heading_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_HEADING)
    value_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_VALUE)
    label_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)

    cx, cy = theme.SCREEN_CENTER
    title_surf = heading_font.render("SYSTEM STATUS", True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 130)))

    rows = [
        ("CPU", _format_percent(stats.cpu_percent), _warn_color(stats.cpu_percent, 85)),
        ("RAM", _format_percent(stats.ram_percent), _warn_color(stats.ram_percent, 90)),
        ("TEMP", _format_temp(stats.cpu_temp_c), _warn_color(stats.cpu_temp_c, 80)),
        ("UPTIME", _format_uptime(stats.uptime_s), theme.TEXT_PRIMARY),
    ]

    y = cy - 60
    for label, value, color in rows:
        label_surf = label_font.render(label, True, theme.TEXT_MUTED)
        surface.blit(label_surf, label_surf.get_rect(center=(cx, y)))
        value_surf = value_font.render(value, True, color)
        surface.blit(value_surf, value_surf.get_rect(center=(cx, y + 24)))
        y += ROW_SPACING


def _warn_color(value: float | None, threshold: float) -> tuple[int, int, int]:
    if value is not None and value >= threshold:
        return theme.WARNING
    return theme.TEXT_PRIMARY


def _format_percent(value: float | None) -> str:
    return f"{value:.0f}%" if value is not None else "N/A"


def _format_temp(value: float | None) -> str:
    return f"{value:.1f} C" if value is not None else "N/A"


def _format_uptime(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    total_minutes = int(seconds // 60)
    days, rem_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(rem_minutes, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"
