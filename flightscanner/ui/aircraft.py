"""Aircraft symbol rendering, trails, label placement, interpolation and
hit-testing.

This module only ever receives already-projected screen coordinates --
it never touches lat/lon, dump1090, or the simulator. That keeps the
rendering pipeline identical regardless of data source.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

import pygame

from flightscanner.adsb.models import Aircraft
from flightscanner.ui import gfx, theme

INTERPOLATION_SECONDS = 2.0  # time to glide from previous to new position
SNAP_DISTANCE_PX = 150  # jumps bigger than this snap instantly instead of gliding
TRACK_STEP_DEG = 3  # sprite rotation is quantised to keep the cache small
SPRITE_SUPERSAMPLE = 4

LABEL_OFFSETS = [
    (12, -12),   # top-right
    (12, 12),    # bottom-right
    (-12, -12),  # top-left (anchored via right-aligned rect below)
    (-12, 12),   # bottom-left
]
LABEL_MAX_RADIUS = theme.RADAR_RADIUS_PX + 6  # keep labels inside the scope

# Top-down airliner silhouette, nose up, in unit coordinates. Right half
# only; the left half is mirrored.
_SILHOUETTE_RIGHT = [
    (0.0, -1.0), (0.09, -0.9), (0.11, -0.3), (0.95, 0.14), (0.95, 0.28),
    (0.11, 0.1), (0.08, 0.6), (0.38, 0.82), (0.38, 0.94), (0.0, 0.86),
]
SILHOUETTE = _SILHOUETTE_RIGHT + [(-x, y) for x, y in reversed(_SILHOUETTE_RIGHT[1:-1])]


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
    """Tracks per-aircraft interpolation state and trails across data refreshes."""

    def __init__(self) -> None:
        self._states: dict[str, _RenderState] = {}
        self._trails: dict[str, deque[tuple[float, float]]] = {}
        self._trail_sampled_at: dict[str, float] = {}

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
            self._trails.pop(icao, None)  # a jump would draw a misleading streak
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

    def record_trail(self, icao: str, pos: tuple[float, float], now: float) -> None:
        """Sample the on-screen position every TRAIL_SAMPLE_SECONDS."""
        if now - self._trail_sampled_at.get(icao, -math.inf) < theme.TRAIL_SAMPLE_SECONDS:
            return
        self._trail_sampled_at[icao] = now
        self._trails.setdefault(icao, deque(maxlen=theme.TRAIL_LENGTH)).append(pos)

    def trail(self, icao: str) -> deque[tuple[float, float]]:
        return self._trails.get(icao, deque())

    def prune(self, live_icaos: set[str]) -> None:
        for icao in list(self._states.keys()):
            if icao not in live_icaos:
                del self._states[icao]
                self._trails.pop(icao, None)
                self._trail_sampled_at.pop(icao, None)

    @staticmethod
    def _interpolated(state: _RenderState, now: float) -> tuple[float, float]:
        elapsed = now - state.target_time + INTERPOLATION_SECONDS
        t = max(0.0, min(1.0, elapsed / INTERPOLATION_SECONDS))
        x = state.prev_pos[0] + (state.target_pos[0] - state.prev_pos[0]) * t
        y = state.prev_pos[1] + (state.target_pos[1] - state.prev_pos[1]) * t
        return x, y


# --- Symbols -----------------------------------------------------------------

@lru_cache(maxsize=64)
def _base_sprite(color: tuple[int, int, int], has_track: bool) -> pygame.Surface:
    """Nose-up sprite drawn at SPRITE_SUPERSAMPLE x and smooth-scaled down."""
    size = theme.AIRCRAFT_SYMBOL_SIZE
    big_size = size * SPRITE_SUPERSAMPLE
    big = pygame.Surface((big_size, big_size), pygame.SRCALPHA)
    half = big_size / 2
    if has_track:
        scale = half * 0.92
        points = [(half + x * scale, half + y * scale) for x, y in SILHOUETTE]
        pygame.draw.polygon(big, color, points)
    else:
        # no heading reported: ring with a centre dot
        pygame.draw.circle(big, color, (half, half), half * 0.55, SPRITE_SUPERSAMPLE * 2)
        pygame.draw.circle(big, color, (half, half), half * 0.18)
    return pygame.transform.smoothscale(big, (size, size))


@lru_cache(maxsize=2048)
def _rotated_sprite(color: tuple[int, int, int], track_step: int | None) -> pygame.Surface:
    if track_step is None:
        return gfx.optimise(_base_sprite(color, False))
    angle = track_step * TRACK_STEP_DEG
    rotated = pygame.transform.rotozoom(_base_sprite(color, True), -angle, 1)
    return gfx.optimise(rotated)


def draw_aircraft_symbol(
    surface: pygame.Surface, pos: tuple[float, float], track: float | None, color: tuple[int, int, int]
) -> None:
    """Draw a top-down aircraft silhouette rotated to `track`.

    Falls back to a ring-and-dot marker if track is unavailable.
    """
    track_step = None if track is None else round(track / TRACK_STEP_DEG) % (360 // TRACK_STEP_DEG)
    sprite = _rotated_sprite(color, track_step)
    surface.blit(sprite, sprite.get_rect(center=(round(pos[0]), round(pos[1]))))


def draw_trail(
    surface: pygame.Surface, points: deque[tuple[float, float]], head: tuple[float, float], color: tuple[int, int, int]
) -> None:
    """Fading line through recent positions, ending at the aircraft."""
    path = list(points) + [head]
    n = len(path)
    if n < 2:
        return
    for i in range(n - 1):
        t = (i + 1) / n  # older segments fade towards the scope background
        seg_color = theme.mix(theme.SCOPE_EDGE, color, 0.15 + 0.6 * t)
        pygame.draw.aaline(surface, seg_color, path[i], path[i + 1])


def draw_selection(surface: pygame.Surface, pos: tuple[float, float], now: float) -> None:
    """Corner-bracket target lock around the selected aircraft."""
    x, y = pos
    breathe = 1.5 * math.sin(now * 3.0)
    half = 17 + breathe
    arm = 6
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = x + sx * half, y + sy * half
            pygame.draw.aaline(surface, theme.SELECTION, (cx, cy), (cx - sx * arm, cy))
            pygame.draw.aaline(surface, theme.SELECTION, (cx, cy), (cx, cy - sy * arm))


def draw_proximity_ring(surface: pygame.Surface, pos: tuple[float, float], now: float) -> None:
    """Pulsing ring drawn around an aircraft within the proximity alert range."""
    pulse = (math.sin(now * theme.ALERT_FLASH_HZ * 2 * math.pi) + 1) / 2  # 0..1
    radius = theme.AIRCRAFT_SYMBOL_SIZE * (0.9 + 0.5 * pulse)
    gfx.blit_glow(surface, theme.ALERT, pos, int(2 + 3 * pulse), size=56)
    gfx.aa_ring(surface, theme.ALERT, pos, radius, theme.LINE_WIDTH_NORMAL)


# --- Labels ------------------------------------------------------------------

@lru_cache(maxsize=1024)
def _label_block(lines: tuple[tuple[str, tuple[int, int, int], int], ...]) -> pygame.Surface:
    """Stack (text, colour, size) lines into one left-aligned surface."""
    surfs = [gfx.text(t, size, color, "mono") for t, color, size in lines]
    width = max(s.get_width() for s in surfs)
    height = sum(s.get_height() for s in surfs) - 3 * (len(surfs) - 1)
    block = pygame.Surface((width, height), pygame.SRCALPHA)
    y = 0
    for s in surfs:
        block.blit(s, (0, y))
        y += s.get_height() - 3
    return gfx.optimise(block)


def draw_label(
    surface: pygame.Surface,
    lines: tuple[tuple[str, tuple[int, int, int], int], ...],
    anchor: tuple[float, float],
    used_rects: list[pygame.Rect],
) -> None:
    """Draw a label block near `anchor`, trying a few candidate positions
    to avoid overlapping previously placed labels or leaving the scope."""
    surf = _label_block(lines)
    ax, ay = anchor

    candidates = []
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
        candidates.append(rect)

    inside = [r for r in candidates if _inside_scope(r)] or candidates
    for rect in inside:
        if not any(rect.colliderect(used) for used in used_rects):
            break
    else:
        rect = inside[0]  # no collision-free spot found -- use the first anyway

    used_rects.append(rect)
    surface.blit(surf, rect)


def _inside_scope(rect: pygame.Rect) -> bool:
    cx, cy = theme.SCREEN_CENTER
    return all(
        math.hypot(x - cx, y - cy) <= LABEL_MAX_RADIUS
        for x, y in (rect.topleft, rect.topright, rect.bottomleft, rect.bottomright)
    )


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
