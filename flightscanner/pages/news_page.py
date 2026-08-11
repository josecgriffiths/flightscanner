"""NEWS page -- RSS headlines via NewsReader. Never required for core
ADS-B operation; fails silently and shows an unavailable state if
offline or unconfigured.
"""
from __future__ import annotations

import textwrap

import pygame

from flightscanner.pages.receiver_page import draw_placeholder
from flightscanner.services.news import NewsReader
from flightscanner.ui import theme

_reader: NewsReader | None = None
_enabled = True

WRAP_CHARS = 34
LINE_SPACING = 22
HEADLINE_SPACING = 10


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

    heading_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_HEADING)
    body_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)

    cx, cy = theme.SCREEN_CENTER
    title_surf = heading_font.render("NEWS", True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 220)))

    y = cy - 160
    for headline in headlines:
        for line in textwrap.wrap(headline, WRAP_CHARS) or [""]:
            line_surf = body_font.render(line, True, theme.TEXT_PRIMARY)
            surface.blit(line_surf, line_surf.get_rect(center=(cx, y)))
            y += LINE_SPACING
        y += HEADLINE_SPACING
