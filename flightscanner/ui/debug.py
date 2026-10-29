"""Developer debug overlay -- toggled with D, never on by default."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from flightscanner.ui import gfx, theme

PANEL_TOPLEFT = (150, 130)  # inside the round panel's visible area
PANEL_SIZE = (300, 176)


@dataclass
class DebugInfo:
    fps: float
    mode: str
    source_aircraft_count: int
    rendered_aircraft_count: int
    selected_icao: str | None
    radar_range_nm: float
    pointer_pos: tuple[int, int]
    last_read_ok_age_s: float | None
    current_page: str


def draw_debug_overlay(surface: pygame.Surface, info: DebugInfo) -> None:
    lines = [
        f"FPS {info.fps:.1f}",
        f"MODE {info.mode}",
        f"PAGE {info.current_page}",
        f"SOURCE AC {info.source_aircraft_count}  RENDERED {info.rendered_aircraft_count}",
        f"SELECTED {info.selected_icao or '-'}",
        f"RANGE {info.radar_range_nm:.0f} NM",
        f"POINTER {info.pointer_pos}",
        f"LAST READ {info.last_read_ok_age_s:.1f}s ago" if info.last_read_ok_age_s is not None else "LAST READ -",
    ]

    surface.blit(gfx.panel(*PANEL_SIZE, radius=12), PANEL_TOPLEFT)
    x, y = PANEL_TOPLEFT[0] + 14, PANEL_TOPLEFT[1] + 12
    for line in lines:
        rect = gfx.blit_text(surface, line, theme.FONT_SIZE_TINY, theme.ACCENT, "mono", topleft=(x, y))
        y = rect.bottom + 3
