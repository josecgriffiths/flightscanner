"""Static radar backdrop: range rings, crosshair, receiver marker, compass."""
from __future__ import annotations

import pygame

from flightscanner.ui import theme

RANGE_STEPS_FRACTIONS = [0.25, 0.5, 0.75, 1.0]


def draw_radar_background(surface: pygame.Surface, radius_px: float) -> None:
    cx, cy = theme.SCREEN_CENTER

    for fraction in RANGE_STEPS_FRACTIONS:
        r = int(radius_px * fraction)
        color = theme.GRID_LINE if fraction == 1.0 else theme.GRID_LINE_FAINT
        pygame.draw.circle(surface, color, (cx, cy), r, theme.LINE_WIDTH_THIN)

    # subtle crosshair
    pygame.draw.line(
        surface, theme.GRID_LINE_FAINT, (cx - radius_px, cy), (cx + radius_px, cy)
    )
    pygame.draw.line(
        surface, theme.GRID_LINE_FAINT, (cx, cy - radius_px), (cx, cy + radius_px)
    )

    _draw_receiver_marker(surface, (cx, cy))
    _draw_compass_labels(surface, (cx, cy), radius_px)


def _draw_receiver_marker(surface: pygame.Surface, center: tuple[int, int]) -> None:
    pygame.draw.circle(surface, theme.RECEIVER_MARKER, center, 4)
    pygame.draw.circle(surface, theme.RECEIVER_MARKER, center, 8, theme.LINE_WIDTH_THIN)


def _draw_compass_labels(
    surface: pygame.Surface, center: tuple[int, int], radius_px: float
) -> None:
    font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
    cx, cy = center
    labels = {
        "N": (cx, cy - radius_px - 18),
        "E": (cx + radius_px + 14, cy),
        "S": (cx, cy + radius_px + 18),
        "W": (cx - radius_px - 14, cy),
    }
    for text, pos in labels.items():
        surf = font.render(text, True, theme.TEXT_MUTED)
        rect = surf.get_rect(center=pos)
        surface.blit(surf, rect)


def draw_range_and_count_labels(
    surface: pygame.Surface, range_nm: float, aircraft_count: int
) -> None:
    font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
    cx = theme.SCREEN_CENTER[0]
    y = theme.SCREEN_HEIGHT - 52

    text = f"{aircraft_count} AIRCRAFT   RANGE {int(range_nm)} NM"
    surf = font.render(text, True, theme.TEXT_MUTED)
    rect = surf.get_rect(center=(cx, y))
    surface.blit(surf, rect)
