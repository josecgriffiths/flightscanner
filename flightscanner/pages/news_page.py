"""NEWS page -- RSS headlines via NewsReader. Never required for core
ADS-B operation; fails silently and shows an unavailable state if
offline or unconfigured.
"""
from __future__ import annotations

import math

import pygame

from flightscanner.pages.receiver_page import draw_placeholder
from flightscanner.services.news import NewsReader
from flightscanner.ui import gfx, theme, widgets

_reader: NewsReader | None = None
_enabled = True

TEXT_RADIUS = 300  # wrap headlines to the circle's width at this radius
SIDE_PADDING = 24
LINE_SPACING = 21
HEADLINE_SPACING = 18
BOTTOM_LIMIT = 250  # px below centre; stop before the page dots


def configure(enabled: bool, feed_url: str, refresh_minutes: float) -> None:
    global _reader, _enabled
    _enabled = enabled
    _reader = NewsReader(feed_url, refresh_minutes) if enabled else None


def draw(surface: pygame.Surface) -> None:
    if not _enabled or _reader is None:
        draw_placeholder(surface, "NEWS")
        return

    headlines = _reader.read()
    if not headlines:
        draw_placeholder(surface, "NEWS")
        return

    cx, cy = theme.SCREEN_CENTER
    y = widgets.draw_page_title(surface, "NEWS", y_offset=-245) + 26
    body = gfx.font(theme.FONT_SIZE_SMALL, "regular")

    for i, headline in enumerate(headlines):
        lines = _wrap_to_circle(headline, body, y)
        if y + len(lines) * LINE_SPACING > cy + BOTTOM_LIMIT:
            break
        if i > 0:
            divider_y = y - HEADLINE_SPACING // 2 - 2
            pygame.draw.line(surface, theme.GRID_LINE_FAINT, (cx - 60, divider_y), (cx + 60, divider_y))
        for line in lines:
            gfx.blit_text(surface, line, theme.FONT_SIZE_SMALL, theme.TEXT_PRIMARY, center=(cx, y + 6))
            y += LINE_SPACING
        y += HEADLINE_SPACING


def _wrap_to_circle(text: str, font: pygame.font.Font, top_y: float) -> list[str]:
    """Word-wrap so each line fits the circle's chord at its height."""
    cy = theme.SCREEN_CENTER[1]
    lines: list[str] = []
    current = ""
    y = top_y
    for word in text.split():
        candidate = f"{current} {word}".strip()
        dy = abs(y - cy)
        chord = 2 * math.sqrt(max(0.0, TEXT_RADIUS ** 2 - dy ** 2)) - 2 * SIDE_PADDING
        if current and font.size(candidate)[0] > chord:
            lines.append(current)
            current = word
            y += LINE_SPACING
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
