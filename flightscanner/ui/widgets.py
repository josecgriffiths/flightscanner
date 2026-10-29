"""Reusable building blocks for the non-radar pages: backdrop, page
title, stat tiles and ring gauges. All laid out for the round panel.
"""
from __future__ import annotations

import math
from functools import lru_cache

import pygame

from flightscanner.ui import gfx, theme

SUPERSAMPLE = 2
GAUGE_SWEEP_DEG = 270  # gauge arcs open at the bottom
GAUGE_THICKNESS = 7
TITLE_OFFSET_Y = -200  # page title position relative to screen centre


def build_page_backdrop() -> pygame.Surface:
    """Scope-style radial gradient filling the round panel, without rings."""
    s = SUPERSAMPLE
    w, h = theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT
    big = pygame.Surface((w * s, h * s))
    big.fill(theme.BACKGROUND)
    cx, cy = theme.SCREEN_CENTER[0] * s, theme.SCREEN_CENTER[1] * s
    radius = theme.SAFE_RADIUS * s
    for r in range(radius, 0, -2):
        t = (1 - r / radius) ** 1.4
        pygame.draw.circle(big, theme.mix(theme.SCOPE_EDGE, theme.SCOPE_CENTER, t), (cx, cy), r)
    pygame.draw.circle(big, theme.GRID_LINE_FAINT, (cx, cy), radius, s)
    surface = pygame.transform.smoothscale(big, (w, h))
    return surface.convert() if pygame.display.get_surface() is not None else surface


def draw_page_title(surface: pygame.Surface, title: str, y_offset: int = TITLE_OFFSET_Y) -> int:
    """Centred page heading with a short accent underline; returns its bottom y."""
    cx, cy = theme.SCREEN_CENTER
    rect = gfx.blit_text(
        surface, title, theme.FONT_SIZE_NORMAL, theme.TEXT_PRIMARY, "semibold", 4,
        center=(cx, cy + y_offset),
    )
    line_y = rect.bottom + 10
    pygame.draw.line(surface, theme.ACCENT, (cx - 18, line_y), (cx + 18, line_y), 2)
    return line_y


def draw_stat_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: str,
    value_color: tuple[int, int, int] = theme.TEXT_PRIMARY,
) -> None:
    surface.blit(gfx.panel(rect.width, rect.height, radius=14), rect)
    gfx.blit_text(
        surface, label, theme.FONT_SIZE_MICRO, theme.TEXT_MUTED, "semibold", theme.TRACKING_LABEL,
        topleft=(rect.left + 16, rect.top + 13),
    )
    gfx.blit_text(
        surface, value, theme.FONT_SIZE_VALUE - 4, value_color, "mono",
        bottomleft=(rect.left + 16, rect.bottom - 9),
    )


def tile_grid(columns: int, rows: int, tile_w: int, tile_h: int, gap: int, center: tuple[int, int]) -> list[pygame.Rect]:
    """Rects for a centred grid of tiles, row by row."""
    total_w = columns * tile_w + (columns - 1) * gap
    total_h = rows * tile_h + (rows - 1) * gap
    left = center[0] - total_w // 2
    top = center[1] - total_h // 2
    return [
        pygame.Rect(left + c * (tile_w + gap), top + r * (tile_h + gap), tile_w, tile_h)
        for r in range(rows)
        for c in range(columns)
    ]


@lru_cache(maxsize=256)
def _gauge_arc(radius: int, fraction_pct: int, color: tuple[int, int, int]) -> pygame.Surface:
    """Track + progress arc, drawn at 2x and smooth-scaled. Cached per 1%."""
    s = SUPERSAMPLE
    size = (radius + GAUGE_THICKNESS) * 2
    big = pygame.Surface((size * s, size * s), pygame.SRCALPHA)
    c = size * s / 2
    r = radius * s
    dot = GAUGE_THICKNESS * s / 2
    start = 180 + (360 - GAUGE_SWEEP_DEG) / 2  # bearing of the arc's start (bottom-left)

    def stroke(sweep_deg: float, col: tuple[int, int, int]) -> None:
        steps = max(2, int(math.radians(sweep_deg) * r / 2))
        for i in range(steps + 1):
            b = math.radians(start + sweep_deg * i / steps)
            pygame.draw.circle(big, col, (c + r * math.sin(b), c - r * math.cos(b)), dot)

    stroke(GAUGE_SWEEP_DEG, theme.GRID_LINE_FAINT)
    if fraction_pct > 0:
        stroke(GAUGE_SWEEP_DEG * fraction_pct / 100, color)
    return gfx.optimise(pygame.transform.smoothscale(big, (size, size)))


def draw_ring_gauge(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    fraction: float | None,
    color: tuple[int, int, int],
    label: str,
    value: str,
) -> None:
    pct = 0 if fraction is None else round(max(0.0, min(1.0, fraction)) * 100)
    arc = _gauge_arc(radius, pct, color)
    surface.blit(arc, arc.get_rect(center=center))
    gfx.blit_text(surface, value, theme.FONT_SIZE_VALUE - 4, theme.TEXT_PRIMARY, "mono",
                  center=(center[0], center[1] - 4))
    gfx.blit_text(surface, label, theme.FONT_SIZE_MICRO, theme.TEXT_MUTED, "semibold",
                  theme.TRACKING_LABEL, center=(center[0], center[1] + radius - 4))
