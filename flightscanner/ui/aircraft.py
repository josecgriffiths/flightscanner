"""Aircraft symbol rendering, label placement, interpolation and hit-testing.

This module only ever receives already-projected screen coordinates --
it never touches lat/lon, dump1090, or the simulator. That keeps the
rendering pipeline identical regardless of data source.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import pygame

from flightscanner.adsb.models import Aircraft
from flightscanner.ui import theme

INTERPOLATION_SECONDS = 2.0  # time to glide from previous to new position
SNAP_DISTANCE_PX = 150  # jumps bigger than this snap instantly instead of gliding

LABEL_OFFSETS = [
    (10, -10),   # top-right
    (10, 10),    # bottom-right
    (-10, -10),  # top-left (anchored via right-aligned rect below)
    (-10, 10),   # bottom-left
]


@dataclass
class _RenderState:
    prev_pos: tuple[float, float]
    target_pos: tuple[float, float]
    target_time: float


@dataclass
class RenderedAircraft:
    aircraft: Aircraft
    screen_pos: tuple[float, float]
    selected: bool = False


class AircraftRenderer:
    """Tracks per-aircraft interpolation state across data refreshes."""

    def __init__(self) -> None:
        self._states: dict[str, _RenderState] = {}

    def set_target(self, icao: str, pos: tuple[float, float], now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        existing = self._states.get(icao)
        if existing is None:
            self._states[icao] = _RenderState(prev_pos=pos, target_pos=pos, target_time=now)
            return

        dist = math.hypot(pos[0] - existing.target_pos[0], pos[1] - existing.target_pos[1])
        current_interp = self._interpolated(existing, now)
        if dist > SNAP_DISTANCE_PX:
            self._states[icao] = _RenderState(prev_pos=pos, target_pos=pos, target_time=now)
        else:
            self._states[icao] = _RenderState(
                prev_pos=current_interp, target_pos=pos, target_time=now
            )

    def get_position(self, icao: str, now: float | None = None) -> tuple[float, float] | None:
        state = self._states.get(icao)
        if state is None:
            return None
        now = now if now is not None else time.monotonic()
        return self._interpolated(state, now)

    def prune(self, live_icaos: set[str]) -> None:
        for icao in list(self._states.keys()):
            if icao not in live_icaos:
                del self._states[icao]

    @staticmethod
    def _interpolated(state: _RenderState, now: float) -> tuple[float, float]:
        elapsed = now - state.target_time + INTERPOLATION_SECONDS
        t = max(0.0, min(1.0, elapsed / INTERPOLATION_SECONDS))
        x = state.prev_pos[0] + (state.target_pos[0] - state.prev_pos[0]) * t
        y = state.prev_pos[1] + (state.target_pos[1] - state.prev_pos[1]) * t
        return x, y


def draw_aircraft_symbol(
    surface: pygame.Surface, pos: tuple[float, float], track: float | None, color: tuple[int, int, int]
) -> None:
    """Draw a small top-down aircraft triangle, rotated to `track`.

    Falls back to a neutral diamond if track is unavailable.
    """
    x, y = pos
    size = theme.AIRCRAFT_SYMBOL_SIZE

    if track is None:
        points = [(x, y - size / 2), (x + size / 2, y), (x, y + size / 2), (x - size / 2, y)]
        pygame.draw.polygon(surface, color, points, theme.LINE_WIDTH_NORMAL)
        return

    angle = math.radians(track)
    # nose, left wingtip, tail, right wingtip -- unrotated, nose pointing up (north)
    local_points = [(0, -size * 0.6), (-size * 0.4, size * 0.4), (0, size * 0.15), (size * 0.4, size * 0.4)]
    # rotate clockwise by `angle` (track is measured clockwise from north)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotated = [
        (x + lx * cos_a - ly * sin_a, y + lx * sin_a + ly * cos_a)
        for lx, ly in local_points
    ]
    pygame.draw.polygon(surface, color, rotated)


def draw_label(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    anchor: tuple[float, float],
    used_rects: list[pygame.Rect],
    color: tuple[int, int, int],
) -> None:
    """Draw a text label near `anchor`, trying a few candidate positions
    to avoid overlapping previously placed labels."""
    surf = font.render(text, True, color)
    ax, ay = anchor

    for dx, dy in LABEL_OFFSETS:
        rect = surf.get_rect()
        if dx >= 0:
            rect.left = ax + dx
        else:
            rect.right = ax + dx
        if dy >= 0:
            rect.top = ay + dy
        else:
            rect.bottom = ay + dy

        if not any(rect.colliderect(used) for used in used_rects):
            used_rects.append(rect)
            surface.blit(surf, rect)
            return

    # No collision-free spot found -- use the first candidate anyway
    rect = surf.get_rect()
    rect.left = ax + LABEL_OFFSETS[0][0]
    rect.top = ay + LABEL_OFFSETS[0][1]
    used_rects.append(rect)
    surface.blit(surf, rect)


def find_nearest_aircraft(
    point: tuple[float, float],
    positions: dict[str, tuple[float, float]],
    touch_radius: float = theme.AIRCRAFT_TOUCH_RADIUS,
) -> str | None:
    """Return the ICAO of the nearest aircraft within touch_radius of point."""
    best_icao: str | None = None
    best_dist = touch_radius
    for icao, pos in positions.items():
        dist = math.hypot(point[0] - pos[0], point[1] - pos[1])
        if dist <= best_dist:
            best_dist = dist
            best_icao = icao
    return best_icao
