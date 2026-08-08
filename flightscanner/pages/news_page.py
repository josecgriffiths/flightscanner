"""NEWS page -- placeholder. Eventually RSS-based; never required for
core ADS-B operation.
"""
from __future__ import annotations

import pygame

from flightscanner.pages.receiver_page import draw_placeholder


def draw(surface: pygame.Surface) -> None:
    draw_placeholder(surface, "NEWS")
