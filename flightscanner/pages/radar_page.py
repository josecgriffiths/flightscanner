"""The primary RADAR page: renders the range rings, moving aircraft,
labels, selection and empty/offline states.
"""
from __future__ import annotations

import time

import pygame

from flightscanner.adsb.geometry import polar_position, project_to_radar
from flightscanner.adsb.models import Aircraft
from flightscanner.ui import aircraft as aircraft_ui
from flightscanner.ui import aircraft_details, radar, theme


class RadarPage:
    def __init__(self, receiver_lat: float | None, receiver_lon: float | None, radar_range_nm: float) -> None:
        self.receiver_lat = receiver_lat
        self.receiver_lon = receiver_lon
        self.radar_range_nm = radar_range_nm
        self.renderer = aircraft_ui.AircraftRenderer()
        self.selected_icao: str | None = None
        self._label_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
        self._last_positions: dict[str, tuple[float, float]] = {}
        self._last_distances: dict[str, float] = {}

    def handle_tap(self, point: tuple[float, float]) -> None:
        hit = aircraft_ui.find_nearest_aircraft(point, self._last_positions)
        self.selected_icao = hit  # tapping empty space deselects

    def update_and_draw(
        self,
        surface: pygame.Surface,
        source_aircraft: list[Aircraft],
        receiver_online: bool,
    ) -> None:
        radar.draw_radar_background(surface, theme.RADAR_RADIUS_PX)

        if self.receiver_lat is None or self.receiver_lon is None:
            self._draw_center_message(surface, ["NO RECEIVER LOCATION", "EDIT config.toml"])
            return

        if not receiver_online:
            self._draw_center_message(surface, ["RECEIVER OFFLINE", "WAITING FOR dump1090-fa"])
            return

        now = time.monotonic()
        positions: dict[str, tuple[float, float]] = {}
        distances: dict[str, float] = {}
        in_range: list[Aircraft] = []

        for ac in source_aircraft:
            if not ac.has_position():
                continue
            polar = polar_position(self.receiver_lat, self.receiver_lon, ac.latitude, ac.longitude)
            if polar.distance_nm > self.radar_range_nm:
                continue
            screen_pos = project_to_radar(
                polar.distance_nm, polar.bearing_deg, theme.SCREEN_CENTER,
                self.radar_range_nm, theme.RADAR_RADIUS_PX,
            )
            self.renderer.set_target(ac.icao, screen_pos, now)
            positions[ac.icao] = screen_pos
            distances[ac.icao] = polar.distance_nm
            in_range.append(ac)

        self.renderer.prune(set(positions.keys()))
        self._last_positions = {icao: self.renderer.get_position(icao, now) for icao in positions}
        self._last_distances = distances

        if self.selected_icao is not None and self.selected_icao not in positions:
            self.selected_icao = None

        used_label_rects: list[pygame.Rect] = []
        for ac in in_range:
            pos = self._last_positions[ac.icao]
            selected = ac.icao == self.selected_icao
            color = theme.AIRCRAFT_SELECTED if selected else (
                theme.AIRCRAFT_STALE if ac.is_stale() else theme.AIRCRAFT_SYMBOL
            )
            aircraft_ui.draw_aircraft_symbol(surface, pos, ac.track, color)
            aircraft_ui.draw_label(
                surface, self._label_font, ac.display_callsign(), pos, used_label_rects, color
            )

        radar.draw_range_and_count_labels(surface, self.radar_range_nm, len(in_range))

        if not in_range:
            self._draw_center_message(surface, ["LISTENING", "1090 MHz", "NO AIRCRAFT CURRENTLY RECEIVED"])

        if self.selected_icao is not None:
            selected_ac = next((a for a in in_range if a.icao == self.selected_icao), None)
            if selected_ac is not None:
                aircraft_details.draw_detail_panel(
                    surface, selected_ac, distances.get(selected_ac.icao)
                )

    def _draw_center_message(self, surface: pygame.Surface, lines: list[str]) -> None:
        font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_NORMAL)
        cx, cy = theme.SCREEN_CENTER
        y = cy - (len(lines) * 16)
        for line in lines:
            surf = font.render(line, True, theme.TEXT_MUTED)
            surface.blit(surf, surf.get_rect(center=(cx, y)))
            y += 32
