"""RECEIVER STATUS page -- placeholder pending stats.json integration.

Will eventually read /run/dump1090-fa/stats.json via a dedicated reader,
kept decoupled from the radar UI.
"""
from __future__ import annotations

import pygame

from flightscanner.ui import theme


def draw(surface: pygame.Surface) -> None:
    draw_placeholder(surface, "RECEIVER STATUS")


def draw_placeholder(surface: pygame.Surface, title: str) -> None:
    font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_NORMAL)
    small = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
    cx, cy = theme.SCREEN_CENTER

    title_surf = font.render(title, True, theme.TEXT_PRIMARY)
    surface.blit(title_surf, title_surf.get_rect(center=(cx, cy - 20)))

    note_surf = small.render("COMING SOON", True, theme.TEXT_MUTED)
    surface.blit(note_surf, note_surf.get_rect(center=(cx, cy + 20)))
