"""SYSTEM STATUS page -- placeholder pending psutil integration.

Will eventually show CPU/RAM/temperature/uptime via flightscanner.system.stats,
cached rather than sampled every frame.
"""
from __future__ import annotations

import pygame

from flightscanner.pages.receiver_page import draw_placeholder


def draw(surface: pygame.Surface) -> None:
    draw_placeholder(surface, "SYSTEM STATUS")
