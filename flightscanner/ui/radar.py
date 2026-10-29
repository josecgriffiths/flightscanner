"""Radar scope: cached static backdrop (gradient, rings, bezel ticks,
compass, altitude legend), the rotating sweep, the receiver marker and
the proximity banner.

The backdrop never changes for a given range, so it is drawn once --
geometry at 2x then smooth-scaled down for anti-aliasing -- and simply
blitted each frame.
"""
from __future__ import annotations

import math

import pygame

from flightscanner.ui import gfx, theme

RANGE_STEPS_FRACTIONS = [0.25, 0.5, 0.75, 1.0]
SUPERSAMPLE = 2
CROSSHAIR_GAP_PX = 14


class RadarBackdrop:
    """Builds and caches the static scope image for one radar range."""

    def __init__(self) -> None:
        self._cache: dict[float, pygame.Surface] = {}

    def draw(self, surface: pygame.Surface, range_nm: float) -> None:
        backdrop = self._cache.get(range_nm)
        if backdrop is None:
            backdrop = _build_backdrop(range_nm)
            self._cache[range_nm] = backdrop
        surface.blit(backdrop, (0, 0))


def _build_backdrop(range_nm: float) -> pygame.Surface:
    s = SUPERSAMPLE
    w, h = theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT
    big = pygame.Surface((w * s, h * s))
    big.fill(theme.BACKGROUND)
    cx, cy = theme.SCREEN_CENTER[0] * s, theme.SCREEN_CENTER[1] * s
    radius = theme.RADAR_RADIUS_PX * s

    # radial gradient: lighter at the centre, fading to the scope edge
    for r in range(radius, 0, -2):
        t = (1 - r / radius) ** 1.4
        pygame.draw.circle(big, theme.mix(theme.SCOPE_EDGE, theme.SCOPE_CENTER, t), (cx, cy), r)

    for fraction in RANGE_STEPS_FRACTIONS:
        color = theme.GRID_LINE if fraction == 1.0 else theme.GRID_LINE_FAINT
        pygame.draw.circle(big, color, (cx, cy), int(radius * fraction), s)

    gap = CROSSHAIR_GAP_PX * s
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(
            big, theme.GRID_LINE_FAINT,
            (cx + dx * gap, cy + dy * gap), (cx + dx * radius, cy + dy * radius), s,
        )

    _draw_ticks(big, (cx, cy), s)
    _draw_altitude_legend_arc(big, (cx, cy), s)
    # thin hairline marking the edge of the round panel
    pygame.draw.circle(big, theme.GRID_LINE_FAINT, (cx, cy), theme.SAFE_RADIUS * s, s)

    surface = pygame.transform.smoothscale(big, (w, h))

    # text is rendered at 1x on top -- fonts are already anti-aliased
    _draw_compass_labels(surface)
    _draw_range_labels(surface, range_nm)
    _draw_altitude_legend_labels(surface)
    return surface.convert() if pygame.display.get_surface() is not None else surface


def _draw_ticks(big: pygame.Surface, center: tuple[int, int], s: int) -> None:
    cx, cy = center
    inner = theme.TICK_INNER_RADIUS * s
    for deg in range(0, 360, 5):
        if deg % 90 == 0:
            length, color, width = theme.TICK_CARDINAL_LENGTH, theme.ACCENT_DIM, 2
        elif deg % 30 == 0:
            length, color, width = theme.TICK_MAJOR_LENGTH, theme.TICK_MAJOR, 2
        else:
            length, color, width = theme.TICK_MINOR_LENGTH, theme.TICK_MINOR, 1
        a = math.radians(deg)
        sin_a, cos_a = math.sin(a), math.cos(a)
        outer = inner + length * s
        pygame.draw.line(
            big, color,
            (cx + inner * sin_a, cy - inner * cos_a),
            (cx + outer * sin_a, cy - outer * cos_a),
            width * s,
        )


def _draw_altitude_legend_arc(big: pygame.Surface, center: tuple[int, int], s: int) -> None:
    """Thin arc in the bezel showing the altitude colour scale."""
    cx, cy = center
    r = theme.BEZEL_TEXT_RADIUS * s
    start, end = theme.BEZEL_LEGEND_START, theme.BEZEL_LEGEND_END
    top_alt = theme.ALTITUDE_STOPS[-1][0]
    steps = 240
    for i in range(steps + 1):
        t = i / steps
        bearing = math.radians(end + (start - end) * t)  # low altitude on the left
        color = theme.altitude_color(top_alt * t)
        pygame.draw.circle(big, color, (cx + r * math.sin(bearing), cy - r * math.cos(bearing)), 1.5 * s)


def _draw_altitude_legend_labels(surface: pygame.Surface) -> None:
    pad = 5
    gfx.arc_text(surface, "0", theme.FONT_SIZE_MICRO, theme.TEXT_MUTED,
                 theme.BEZEL_TEXT_RADIUS, theme.BEZEL_LEGEND_END + pad, role="mono")
    gfx.arc_text(surface, "40K FT", theme.FONT_SIZE_MICRO, theme.TEXT_MUTED,
                 theme.BEZEL_TEXT_RADIUS, theme.BEZEL_LEGEND_START - pad - 6, role="mono", tracking=1)


def _draw_compass_labels(surface: pygame.Surface) -> None:
    for text, bearing in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        color = theme.ACCENT if text == "N" else theme.TEXT_SECONDARY
        gfx.blit_text(
            surface, text, theme.FONT_SIZE_SMALL, color, "semibold",
            center=gfx.polar(bearing, theme.COMPASS_LABEL_RADIUS),
        )


def _draw_range_labels(surface: pygame.Surface, range_nm: float) -> None:
    for fraction in RANGE_STEPS_FRACTIONS:
        r = theme.RADAR_RADIUS_PX * fraction
        label = f"{range_nm * fraction:g}"
        if fraction == 1.0:
            label += " NM"
        pos = gfx.polar(theme.RANGE_LABEL_BEARING, r)
        surf = gfx.text(label, theme.FONT_SIZE_MICRO, theme.TEXT_MUTED, "mono")
        rect = surf.get_rect(center=pos).inflate(6, 2)
        # punch a gap in the ring using the gradient colour underneath
        surface.fill(surface.get_at((rect.centerx, rect.top - 2)), rect)
        surface.blit(surf, surf.get_rect(center=rect.center))


class Sweep:
    """Rotating radar sweep: a fading wedge trailing a bright leading edge.

    The wedge is pre-rendered into one quadrant-sized image whose
    bottom-right corner is the pivot, so each frame only rotates a
    300x300 image rather than the whole scope.
    """

    def __init__(self) -> None:
        self._wedge: pygame.Surface | None = None

    def angle(self, now: float) -> float:
        """Current sweep bearing in degrees (0 = north, clockwise)."""
        return (now / theme.SWEEP_PERIOD_SECONDS * 360.0) % 360.0

    def draw(self, surface: pygame.Surface, now: float) -> None:
        if self._wedge is None:
            self._wedge = _build_wedge()
        angle = self.angle(now)
        cx, cy = theme.SCREEN_CENTER
        half = theme.RADAR_RADIUS_PX / 2

        rotated = pygame.transform.rotate(self._wedge, -angle)
        a = math.radians(angle)
        # wedge image centre sits at (-half, -half) from the pivot; rotate that offset
        ox = -half * math.cos(a) + half * math.sin(a)
        oy = -half * math.sin(a) - half * math.cos(a)
        surface.blit(rotated, rotated.get_rect(center=(cx + ox, cy + oy)))

        pygame.draw.aaline(surface, theme.ACCENT, (cx, cy), gfx.polar(angle, theme.RADAR_RADIUS_PX - 1))


def _build_wedge() -> pygame.Surface:
    r = theme.RADAR_RADIUS_PX
    wedge = pygame.Surface((r, r), pygame.SRCALPHA)
    pivot = (r, r)
    step = 0.5
    trail = theme.SWEEP_TRAIL_DEG
    color = theme.ACCENT

    def point(bearing_deg: float) -> tuple[float, float]:
        b = math.radians(bearing_deg)
        return r + r * math.sin(b), r - r * math.cos(b)

    b = -trail
    while b < 0:
        t = (b + trail) / trail  # 0 at the tail, 1 at the leading edge
        alpha = int(theme.SWEEP_MAX_ALPHA * t ** 2.2)
        pygame.draw.polygon(wedge, (*color, alpha), [pivot, point(b), point(min(0.0, b + step * 1.5))])
        b += step
    return wedge.convert_alpha() if pygame.display.get_surface() is not None else wedge


def draw_receiver_marker(surface: pygame.Surface, now: float) -> None:
    """Receiver position at the scope centre, with a slow outward pulse."""
    center = theme.SCREEN_CENTER
    phase = (now / 2.4) % 1.0
    pulse_color = theme.mix(theme.ACCENT, theme.SCOPE_CENTER, phase)
    gfx.aa_ring(surface, pulse_color, center, 6 + 14 * phase)
    gfx.blit_glow(surface, theme.ACCENT, center, 2, size=28)
    gfx.aa_dot(surface, theme.RECEIVER_MARKER, center, 3)


def draw_listening_ripples(surface: pygame.Surface, now: float) -> None:
    """Expanding rings shown while no aircraft are in range."""
    for i in range(3):
        phase = ((now / 3.0) + i / 3) % 1.0
        color = theme.mix(theme.ACCENT_DIM, theme.SCOPE_EDGE, phase)
        gfx.aa_ring(surface, color, theme.SCREEN_CENTER, 20 + phase * (theme.RADAR_RADIUS_PX - 30))


def draw_proximity_banner(surface: pygame.Surface, distance_nm: float, now: float, y: float) -> None:
    """Pulsing pill banner shown when an aircraft is within alert range."""
    pulse = (math.sin(now * theme.ALERT_FLASH_HZ * 2 * math.pi) + 1) / 2  # 0..1
    border = theme.mix(theme.PANEL_BORDER, theme.ALERT, 0.4 + 0.6 * pulse)
    width, height = 280, 40
    pill = gfx.panel(width, height, fill=(40, 8, 12, 225), border=border, radius=height // 2)
    rect = pill.get_rect(center=(theme.SCREEN_CENTER[0], y))
    surface.blit(pill, rect)

    gfx.blit_glow(surface, theme.ALERT, (rect.left + 22, rect.centery), int(2 + 3 * pulse), size=30)
    gfx.aa_dot(surface, theme.ALERT, (rect.left + 22, rect.centery), 4)
    label = gfx.text("OVERHEAD", theme.FONT_SIZE_TINY, theme.ALERT, "semibold", theme.TRACKING_LABEL)
    value = gfx.text(f"{distance_nm:.2f} NM", theme.FONT_SIZE_NORMAL, theme.TEXT_PRIMARY, "mono")
    x = rect.left + 40
    surface.blit(label, label.get_rect(midleft=(x, rect.centery)))
    surface.blit(value, value.get_rect(midright=(rect.right - 20, rect.centery)))
