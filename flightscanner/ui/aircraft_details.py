"""Selected-aircraft detail panel.

Only shows fields that are actually present -- never renders "None" and
never invents data (airline, route, registration) that dump1090 does not
provide.
"""
from __future__ import annotations

import pygame

from flightscanner.adsb.models import Aircraft
from flightscanner.ui import theme


def build_detail_rows(aircraft: Aircraft, distance_nm: float | None) -> list[str]:
    rows = [aircraft.display_callsign()]

    altitude = aircraft.display_altitude()
    if altitude:
        rows.append(altitude)

    speed = aircraft.display_speed()
    if speed:
        rows.append(speed)

    track = aircraft.display_track()
    if track:
        rows.append(track)

    vrate = aircraft.display_vertical_rate()
    if vrate:
        rows.append(vrate)

    if distance_nm is not None:
        rows.append(f"{distance_nm:.1f} NM")

    rows.append(f"ICAO {aircraft.icao.upper()}")

    if aircraft.squawk:
        rows.append(f"SQUAWK {aircraft.squawk}")

    if aircraft.rssi is not None:
        rows.append(f"SIGNAL {aircraft.rssi:.1f} dB")

    if aircraft.seen is not None:
        rows.append(f"LAST SEEN {aircraft.seen:.1f}s")

    return rows


def draw_detail_panel(surface: pygame.Surface, aircraft: Aircraft, distance_nm: float | None) -> None:
    rows = build_detail_rows(aircraft, distance_nm)
    heading_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_HEADING)
    body_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_NORMAL)

    cx, cy = theme.SCREEN_CENTER
    y = cy - 140

    heading_surf = heading_font.render(rows[0], True, theme.TEXT_PRIMARY)
    surface.blit(heading_surf, heading_surf.get_rect(center=(cx, y)))
    y += 50

    for row in rows[1:]:
        surf = body_font.render(row, True, theme.TEXT_MUTED)
        surface.blit(surf, surf.get_rect(center=(cx, y)))
        y += 32
