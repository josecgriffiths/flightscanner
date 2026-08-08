"""WEATHER page -- placeholder. Never required for radar to function;
a future WeatherService must fail silently if offline.
"""
from __future__ import annotations

import pygame

from flightscanner.pages.receiver_page import draw_placeholder


def draw(surface: pygame.Surface) -> None:
    draw_placeholder(surface, "WEATHER")
