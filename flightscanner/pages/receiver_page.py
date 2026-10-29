"""RECEIVER STATUS page -- reads dump1090-fa's stats.json via
ReceiverStatsReader, kept decoupled from the radar UI's aircraft.json
reading.

`configure()` must be called once at startup with the stats.json path
before `draw()` is used; App wires this up from config.data.stats_path.
"""
from __future__ import annotations

import pygame

from flightscanner.adsb.receiver_stats import ReceiverStatsReader
from flightscanner.ui import gfx, theme, widgets

_reader: ReceiverStatsReader | None = None

TILE_WIDTH = 196
TILE_HEIGHT = 74
TILE_GAP = 14


def configure(stats_path: str) -> None:
    global _reader
    _reader = ReceiverStatsReader(stats_path)


def draw(surface: pygame.Surface) -> None:
    stats = _reader.read() if _reader is not None else None

    widgets.draw_page_title(surface, "RECEIVER")
    cx, cy = theme.SCREEN_CENTER

    if stats is None:
        gfx.blit_text(surface, "No data from dump1090-fa", theme.FONT_SIZE_SMALL,
                      theme.TEXT_MUTED, center=(cx, cy))
        return

    rows = [
        ("MESSAGES / SEC", _format_rate(stats.messages_per_second)),
        ("MESSAGES TOTAL", _format_count(stats.messages_total)),
        ("SIGNAL", _format_db(stats.signal_dbfs)),
        ("NOISE", _format_db(stats.noise_dbfs)),
        ("STRONG SIGNALS", _format_count(stats.strong_signals)),
        ("POSITIONS / MIN", _format_count(stats.position_count)),
    ]

    rects = widgets.tile_grid(2, 3, TILE_WIDTH, TILE_HEIGHT, TILE_GAP, (cx, cy + 30))
    for rect, (label, value) in zip(rects, rows):
        color = theme.ACCENT if label.startswith("MESSAGES / SEC") else theme.TEXT_PRIMARY
        widgets.draw_stat_tile(surface, rect, label, value, color)


def draw_placeholder(surface: pygame.Surface, title: str) -> None:
    """Used by WEATHER/NEWS pages when their data source is unavailable."""
    widgets.draw_page_title(surface, title)
    cx, cy = theme.SCREEN_CENTER
    gfx.blit_text(surface, "Not available right now", theme.FONT_SIZE_SMALL,
                  theme.TEXT_MUTED, center=(cx, cy))


def _format_rate(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "N/A"


def _format_count(value: int | None) -> str:
    return f"{value:,}" if value is not None else "N/A"


def _format_db(value: float | None) -> str:
    return f"{value:.1f} dBFS" if value is not None else "N/A"
