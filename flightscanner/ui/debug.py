"""Developer debug overlay -- toggled with D, never on by default."""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from flightscanner.ui import theme


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
    font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
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

    x, y = 10, 50
    for line in lines:
        surf = font.render(line, True, theme.ACCENT)
        surface.blit(surf, (x, y))
        y += surf.get_height() + 2
