"""Page state machine and the small dot page indicator."""
from __future__ import annotations

from enum import Enum

import pygame

from flightscanner.ui import theme


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
    if current not in PAGE_ORDER:
        return
    dot_radius = 4
    spacing = 16
    count = len(PAGE_ORDER)
    total_width = spacing * (count - 1)
    start_x = theme.SCREEN_CENTER[0] - total_width // 2
    y = theme.SCREEN_HEIGHT - 28

    for i, page in enumerate(PAGE_ORDER):
        x = start_x + i * spacing
        color = theme.ACCENT if page == current else theme.GRID_LINE
        pygame.draw.circle(surface, color, (x, y), dot_radius)
