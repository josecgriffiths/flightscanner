"""Shared drawing primitives: cached fonts/text, curved bezel text,
translucent panels, glow sprites and anti-aliased shapes.

Everything expensive to build (fonts, rendered text, glow sprites, panel
backgrounds) is cached, so per-frame drawing is mostly blits. That matters
on a Raspberry Pi, where re-creating a Font every frame -- what the pages
used to do -- costs more than drawing the whole radar.
"""
from __future__ import annotations

import logging
import math
from functools import lru_cache
from pathlib import Path

import pygame
import pygame.gfxdraw

from flightscanner.ui import theme

logger = logging.getLogger(__name__)

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

Color = tuple[int, int, int]


# --- Fonts / text --------------------------------------------------------

@lru_cache(maxsize=None)
def font(size: int, role: str = "regular") -> pygame.font.Font:
    path = FONT_DIR / theme.FONT_FILES.get(role, "")
    if path.is_file():
        return pygame.font.Font(str(path), size)
    logger.warning("Font %s missing; falling back to pygame default", path)
    return pygame.font.Font(None, round(size * 1.3))  # default font runs small


@lru_cache(maxsize=2048)
def text(
    content: str, size: int, color: Color, role: str = "regular", tracking: int = 0
) -> pygame.Surface:
    """Rendered text surface. `tracking` adds px of letter spacing."""
    f = font(size, role)
    if tracking == 0 or len(content) < 2:
        return optimise(f.render(content, True, color))

    glyphs = [f.render(ch, True, color) for ch in content]
    width = sum(g.get_width() for g in glyphs) + tracking * (len(glyphs) - 1)
    out = pygame.Surface((width, f.get_height()), pygame.SRCALPHA)
    x = 0
    for g in glyphs:
        out.blit(g, (x, 0))
        x += g.get_width() + tracking
    return optimise(out)


def blit_text(
    surface: pygame.Surface,
    content: str,
    size: int,
    color: Color,
    role: str = "regular",
    tracking: int = 0,
    **anchor: tuple[float, float] | float,
) -> pygame.Rect:
    """Render and blit text; position with a Rect keyword, e.g. center=(x, y)."""
    surf = text(content, size, color, role, tracking)
    rect = surf.get_rect(**anchor)
    surface.blit(surf, rect)
    return rect


@lru_cache(maxsize=256)
def _arc_glyphs(
    content: str, size: int, color: Color, role: str, tracking: int,
    radius: float, center_bearing: float,
) -> list[tuple[pygame.Surface, tuple[float, float]]]:
    f = font(size, role)
    widths = [f.size(ch)[0] for ch in content]
    total = sum(widths) + tracking * (len(content) - 1)

    # Text centred on the bottom half reads anticlockwise so it stays upright.
    bottom = math.cos(math.radians(center_bearing)) < 0
    direction = -1 if bottom else 1
    bearing = math.radians(center_bearing) - direction * total / (2 * radius)

    cx, cy = theme.SCREEN_CENTER
    placed = []
    for ch, w in zip(content, widths):
        mid = bearing + direction * (w / 2) / radius
        deg = math.degrees(mid)
        glyph = f.render(ch, True, color)
        rotated = pygame.transform.rotozoom(glyph, (180 - deg) if bottom else -deg, 1)
        pos = (cx + radius * math.sin(mid), cy - radius * math.cos(mid))
        placed.append((optimise(rotated), pos))
        bearing += direction * (w + tracking) / radius
    return placed


def arc_text(
    surface: pygame.Surface,
    content: str,
    size: int,
    color: Color,
    radius: float,
    center_bearing: float,
    role: str = "semibold",
    tracking: int = theme.TRACKING_LABEL,
) -> None:
    """Draw text curved along a circle around the screen centre.

    `center_bearing` is degrees clockwise from north (0 = top of screen).
    """
    for glyph, pos in _arc_glyphs(content, size, color, role, tracking, radius, center_bearing):
        surface.blit(glyph, glyph.get_rect(center=pos))


# --- Panels ---------------------------------------------------------------

@lru_cache(maxsize=64)
def panel(
    width: int,
    height: int,
    fill: tuple[int, int, int, int] = theme.PANEL_FILL,
    border: Color | None = theme.PANEL_BORDER,
    radius: int = theme.PANEL_RADIUS,
) -> pygame.Surface:
    """Rounded translucent card, drawn at 2x and scaled down for smooth corners."""
    scale = 2
    big = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    rect = big.get_rect()
    pygame.draw.rect(big, fill, rect, border_radius=radius * scale)
    if border is not None:
        pygame.draw.rect(big, (*border, 255), rect, width=scale, border_radius=radius * scale)
    return optimise(pygame.transform.smoothscale(big, (width, height)))


# --- Glow -------------------------------------------------------------------

GLOW_LEVELS = 6


@lru_cache(maxsize=512)
def glow(color: Color, level: int = GLOW_LEVELS - 1, size: int = theme.GLOW_SIZE) -> pygame.Surface:
    """Soft radial glow. Blit with special_flags=pygame.BLEND_ADD.

    `level` (0..GLOW_LEVELS-1) scales brightness; quantised so the cache
    stays small while the sweep animates it.
    """
    intensity = 0.18 + 0.5 * level / (GLOW_LEVELS - 1)
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    half = size / 2
    steps = int(half)
    for i in range(steps, 0, -1):
        falloff = (1 - i / steps) ** 2.2
        c = tuple(min(255, int(ch * falloff * intensity)) for ch in color)
        pygame.draw.circle(surf, c, (half, half), i)
    return surf


def blit_glow(surface: pygame.Surface, color: Color, pos: tuple[float, float], level: int, size: int = theme.GLOW_SIZE) -> None:
    g = glow(color, max(0, min(GLOW_LEVELS - 1, level)), size)
    surface.blit(g, g.get_rect(center=(round(pos[0]), round(pos[1]))), special_flags=pygame.BLEND_ADD)


# --- Anti-aliased shapes ---------------------------------------------------

def aa_ring(surface: pygame.Surface, color: Color, center: tuple[float, float], radius: float, width: int = 1) -> None:
    x, y = round(center[0]), round(center[1])
    for i in range(width):
        r = round(radius) - i
        if r > 0:
            pygame.gfxdraw.aacircle(surface, x, y, r, color)


def aa_dot(surface: pygame.Surface, color: Color, center: tuple[float, float], radius: float) -> None:
    x, y, r = round(center[0]), round(center[1]), max(1, round(radius))
    pygame.gfxdraw.aacircle(surface, x, y, r, color)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)


def polar(bearing_deg: float, radius: float) -> tuple[float, float]:
    """Screen point at `radius` from centre along a compass bearing."""
    cx, cy = theme.SCREEN_CENTER
    b = math.radians(bearing_deg)
    return cx + radius * math.sin(b), cy - radius * math.cos(b)


def optimise(surf: pygame.Surface) -> pygame.Surface:
    """convert_alpha() once a display exists -- much faster to blit."""
    if pygame.display.get_surface() is not None:
        return surf.convert_alpha()
    return surf
