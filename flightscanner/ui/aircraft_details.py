"""Selected-aircraft detail card.

Only shows fields that are actually present -- never renders "None" and
never invents data (airline, route, registration) that dump1090 does not
provide.
"""
from __future__ import annotations

import pygame

from flightscanner.adsb.models import Aircraft
from flightscanner.ui import gfx, theme

PADDING = 20
GRID_COLUMNS = 3
GRID_ROW_HEIGHT = 44


def build_detail_fields(aircraft: Aircraft, distance_nm: float | None) -> list[tuple[str, str]]:
    """(label, value) pairs for the card grid, in display order."""
    fields: list[tuple[str, str]] = []

    altitude = aircraft.display_altitude()
    if altitude:
        fields.append(("ALTITUDE", altitude))

    speed = aircraft.display_speed()
    if speed:
        fields.append(("SPEED", speed))

    track = aircraft.display_track()
    if track:
        fields.append(("TRACK", track))

    if aircraft.vertical_rate is not None:
        sign = "+" if aircraft.vertical_rate >= 0 else "-"
        fields.append(("V/S FPM", f"{sign}{abs(round(aircraft.vertical_rate)):,}"))

    if distance_nm is not None:
        fields.append(("DISTANCE", f"{distance_nm:.1f} NM"))

    if aircraft.rssi is not None:
        fields.append(("SIGNAL", f"{aircraft.rssi:.1f} dB"))

    return fields[: GRID_COLUMNS * 2]


def build_subtitle(aircraft: Aircraft) -> tuple[str, tuple[int, int, int]]:
    if aircraft.emergency and aircraft.emergency != "none":
        return f"EMERGENCY  {aircraft.emergency.upper()}", theme.ALERT

    parts = [f"ICAO {aircraft.icao.upper()}"]
    if aircraft.squawk:
        parts.append(f"SQUAWK {aircraft.squawk}")
    if aircraft.is_stale(5.0):
        parts.append(f"SEEN {aircraft.seen:.0f}s AGO")
    return "  ·  ".join(parts), theme.TEXT_MUTED


def card_rect(aircraft_pos: tuple[float, float]) -> pygame.Rect:
    """Place the card on the half of the scope away from the aircraft."""
    cx, cy = theme.SCREEN_CENTER
    rect = pygame.Rect(0, 0, theme.DETAIL_CARD_WIDTH, theme.DETAIL_CARD_HEIGHT)
    if aircraft_pos[1] < cy:
        rect.midtop = (cx, cy + theme.DETAIL_CARD_OFFSET)
    else:
        rect.midbottom = (cx, cy - theme.DETAIL_CARD_OFFSET)
    return rect


def draw_detail_panel(
    surface: pygame.Surface, aircraft: Aircraft, distance_nm: float | None, rect: pygame.Rect
) -> None:
    accent = theme.altitude_color(aircraft.altitude_ft(), aircraft.is_ground())
    surface.blit(gfx.panel(rect.width, rect.height), rect)

    left = rect.left + PADDING
    right = rect.right - PADDING

    # header: callsign + altitude-coloured status dot
    title = gfx.blit_text(
        surface, aircraft.display_callsign(), theme.FONT_SIZE_HEADING, theme.TEXT_PRIMARY,
        "mono_bold", topleft=(left, rect.top + 12),
    )
    dot = (right - 6, title.centery)
    gfx.blit_glow(surface, accent, dot, 4, size=34)
    gfx.aa_dot(surface, accent, dot, 5)

    subtitle, sub_color = build_subtitle(aircraft)
    gfx.blit_text(
        surface, subtitle, theme.FONT_SIZE_MICRO, sub_color, "semibold", 1,
        topleft=(left, title.bottom + 2),
    )

    divider_y = title.bottom + 22
    pygame.draw.line(surface, theme.PANEL_BORDER, (left, divider_y), (right, divider_y))

    col_width = (right - left) / GRID_COLUMNS
    for i, (label, value) in enumerate(build_detail_fields(aircraft, distance_nm)):
        col, row = i % GRID_COLUMNS, i // GRID_COLUMNS
        x = left + col * col_width
        y = divider_y + 10 + row * GRID_ROW_HEIGHT
        gfx.blit_text(
            surface, label, theme.FONT_SIZE_MICRO, theme.TEXT_MUTED, "semibold",
            theme.TRACKING_LABEL, topleft=(x, y),
        )
        value_color = accent if label == "ALTITUDE" else theme.TEXT_PRIMARY
        gfx.blit_text(surface, value, theme.FONT_SIZE_SMALL + 2, value_color, "mono", topleft=(x, y + 14))
