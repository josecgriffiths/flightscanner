"""RECEIVER STATUS page -- reads dump1090-fa's stats.json via
ReceiverStatsReader, kept decoupled from the radar UI's aircraft.json
reading.

`configure()` must be called once at startup with the stats.json path
before `draw()` is used; App wires this up from config.data.stats_path.
"""
from __future__ import annotations

import pygame

from flightscanner.adsb.receiver_stats import ReceiverStatsReader
from flightscanner.ui import theme

_reader: ReceiverStatsReader | None = None

ROW_SPACING = 44


def configure(stats_path: str) -> None:
    global _reader
    _reader = ReceiverStatsReader(stats_path)


def draw(surface: pygame.Surface) -> None:
    stats = _reader.read() if _reader is not None else None

    heading_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_HEADING)
    value_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_VALUE)
    label_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)

    cx, cy = theme.SCREEN_CENTER
    title_surf = heading_font.render("RECEIVER STATUS", True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 150)))

    if stats is None:
        note_surf = label_font.render("NO DATA FROM dump1090-fa", True, theme.TEXT_MUTED)
        surface.blit(note_surf, note_surf.get_rect(center=(cx, cy)))
        return

    rows = [
        ("MESSAGES/SEC", _format_rate(stats.messages_per_second)),
        ("MESSAGES TOTAL", _format_count(stats.messages_total)),
        ("SIGNAL", _format_db(stats.signal_dbfs)),
        ("NOISE", _format_db(stats.noise_dbfs)),
        ("STRONG SIGNALS", _format_count(stats.strong_signals)),
        ("POSITIONS/MIN", _format_count(stats.position_count)),
    ]

    y = cy - 80
    for label, value in rows:
        label_surf = label_font.render(label, True, theme.TEXT_MUTED)
        surface.blit(label_surf, label_surf.get_rect(center=(cx, y)))
        value_surf = value_font.render(value, True, theme.TEXT_PRIMARY)
        surface.blit(value_surf, value_surf.get_rect(center=(cx, y + 24)))
        y += ROW_SPACING


def draw_placeholder(surface: pygame.Surface, title: str) -> None:
    """Used by WEATHER/NEWS pages, which have no dedicated data source yet."""
    font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_NORMAL)
    small = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
    cx, cy = theme.SCREEN_CENTER

    title_surf = font.render(title, True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 20)))

    note_surf = small.render("COMING SOON", True, theme.TEXT_MUTED)
    surface.blit(note_surf, note_surf.get_rect(center=(cx, cy + 20)))


def _format_rate(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "N/A"


def _format_count(value: int | None) -> str:
    return f"{value:,}" if value is not None else "N/A"


def _format_db(value: float | None) -> str:
    return f"{value:.1f} dBFS" if value is not None else "N/A"
