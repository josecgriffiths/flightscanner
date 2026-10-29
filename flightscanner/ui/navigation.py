"""Page state machine and the curved page-dot indicator."""
from __future__ import annotations

from enum import Enum

import pygame

from flightscanner.ui import gfx, theme


class Page(Enum):
    RADAR = 0
    AIRCRAFT = 1
    RECEIVER = 2
    SYSTEM = 3
    WEATHER = 4
    NEWS = 5


PAGE_ORDER = [
    Page.RADAR,
    Page.RECEIVER,
    Page.SYSTEM,
    Page.WEATHER,
    Page.NEWS,
]


def next_page(current: Page) -> Page:
    idx = PAGE_ORDER.index(current)
    return PAGE_ORDER[(idx + 1) % len(PAGE_ORDER)]


def previous_page(current: Page) -> Page:
    idx = PAGE_ORDER.index(current)
    return PAGE_ORDER[(idx - 1) % len(PAGE_ORDER)]


def draw_page_indicator(surface: pygame.Surface, current: Page) -> None:
    """Dots along the bottom of the bezel, following the circle."""
    if current not in PAGE_ORDER:
        return
    count = len(PAGE_ORDER)
    # bearing 180 is bottom centre; increasing bearing moves left on the bottom arc
    first = 180 + theme.PAGE_DOT_SPACING_DEG * (count - 1) / 2

    for i, page in enumerate(PAGE_ORDER):
        pos = gfx.polar(first - i * theme.PAGE_DOT_SPACING_DEG, theme.PAGE_DOT_RADIUS)
        if page == current:
            gfx.blit_glow(surface, theme.ACCENT, pos, 3, size=22)
            gfx.aa_dot(surface, theme.ACCENT, pos, 4)
        else:
            gfx.aa_dot(surface, theme.GRID_LINE, pos, 3)
