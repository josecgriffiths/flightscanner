"""The primary RADAR page: renders the scope, sweep, moving aircraft with
trails, labels, selection and empty/offline states.
"""
from __future__ import annotations

import math
import time

import pygame

from flightscanner.adsb.geometry import polar_position, project_to_radar
from flightscanner.adsb.models import Aircraft
from flightscanner.ui import aircraft as aircraft_ui
from flightscanner.ui import aircraft_details, gfx, radar, theme

STALE_FADE = 0.55  # how far stale aircraft fade towards the background
VERTICAL_TREND_FPM = 300  # show a climb/descend arrow beyond this rate
PROXIMITY_BANNER_OFFSET = 215  # px from centre


class RadarPage:
    def __init__(
        self,
        receiver_lat: float | None,
        receiver_lon: float | None,
        radar_range_nm: float,
        proximity_alert_nm: float = 1.0,
        show_altitude_labels: bool = True,
        effects: bool = True,
    ) -> None:
        self.receiver_lat = receiver_lat
        self.receiver_lon = receiver_lon
        self.radar_range_nm = radar_range_nm
        self.proximity_alert_nm = proximity_alert_nm
        self.show_altitude_labels = show_altitude_labels
        self.effects = effects
        self.renderer = aircraft_ui.AircraftRenderer()
        self.backdrop = radar.RadarBackdrop()
        self.sweep = radar.Sweep()
        self.selected_icao: str | None = None
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
        now = time.monotonic()
        self.backdrop.draw(surface, self.radar_range_nm)

        if self.receiver_lat is None or self.receiver_lon is None:
            self._draw_status_card(surface, "NO RECEIVER LOCATION", "Edit config.toml", theme.WARNING)
            return

        if not receiver_online:
            radar.draw_receiver_marker(surface, now)
            self._draw_status_card(surface, "RECEIVER OFFLINE", "Waiting for dump1090-fa", theme.WARNING)
            return

        if self.effects:
            self.sweep.draw(surface, now)

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

        if not in_range:
            radar.draw_listening_ripples(surface, now)

        radar.draw_receiver_marker(surface, now)

        # draw far-to-near so close (more relevant) aircraft end up on top
        in_range.sort(key=lambda a: -distances[a.icao])
        colors = {ac.icao: self._aircraft_color(ac) for ac in in_range}

        for ac in in_range:
            pos = self._last_positions[ac.icao]
            self.renderer.record_trail(ac.icao, pos, now)
            aircraft_ui.draw_trail(surface, self.renderer.trail(ac.icao), pos, colors[ac.icao])

        selected_ac = next((a for a in in_range if a.icao == self.selected_icao), None)
        card = None
        if selected_ac is not None:
            card = aircraft_details.card_rect(self._last_positions[selected_ac.icao])

        sweep_angle = self.sweep.angle(now) if self.effects else None
        # seeding with the card makes labels steer clear of it
        used_label_rects: list[pygame.Rect] = [card] if card is not None else []
        nearest_alert_nm: float | None = None
        for ac in in_range:
            pos = self._last_positions[ac.icao]
            color = colors[ac.icao]
            in_alert_range = (
                self.proximity_alert_nm > 0 and distances[ac.icao] <= self.proximity_alert_nm
            )
            if in_alert_range:
                aircraft_ui.draw_proximity_ring(surface, pos, now)
                nearest_alert_nm = min(nearest_alert_nm or distances[ac.icao], distances[ac.icao])
            if sweep_angle is not None:
                gfx.blit_glow(surface, color, pos, self._glow_level(pos, sweep_angle))
            aircraft_ui.draw_aircraft_symbol(surface, pos, ac.track, color)
            if card is None or not card.inflate(16, 16).collidepoint(pos):
                aircraft_ui.draw_label(surface, self._label_lines(ac, color), pos, used_label_rects)

        gfx.arc_text(
            surface, f"{len(in_range)} AIRCRAFT", theme.FONT_SIZE_TINY, theme.TEXT_SECONDARY,
            theme.BEZEL_TEXT_RADIUS, theme.BEZEL_COUNT_ANGLE,
        )

        if not in_range:
            cx, cy = theme.SCREEN_CENTER
            gfx.blit_text(
                surface, "LISTENING ON 1090 MHz", theme.FONT_SIZE_SMALL, theme.TEXT_SECONDARY,
                "semibold", theme.TRACKING_LABEL, center=(cx, cy + 48),
            )
            gfx.blit_text(
                surface, "No aircraft in range", theme.FONT_SIZE_TINY, theme.TEXT_MUTED,
                center=(cx, cy + 72),
            )

        if selected_ac is not None and card is not None:
            aircraft_ui.draw_selection(surface, self._last_positions[selected_ac.icao], now)
            aircraft_details.draw_detail_panel(
                surface, selected_ac, distances.get(selected_ac.icao), card
            )

        if nearest_alert_nm is not None:
            card_on_top = card is not None and card.bottom < theme.SCREEN_CENTER[1]
            offset = PROXIMITY_BANNER_OFFSET if card_on_top else -PROXIMITY_BANNER_OFFSET
            radar.draw_proximity_banner(surface, nearest_alert_nm, now, theme.SCREEN_CENTER[1] + offset)

    def _aircraft_color(self, ac: Aircraft) -> tuple[int, int, int]:
        color = theme.altitude_color(ac.altitude_ft(), ac.is_ground())
        if ac.is_stale():
            color = theme.mix(color, theme.SCOPE_EDGE, STALE_FADE)
        return color

    def _label_lines(self, ac: Aircraft, color: tuple[int, int, int]) -> tuple:
        callsign_color = theme.TEXT_MUTED if ac.is_stale() else theme.TEXT_PRIMARY
        lines = [(ac.display_callsign(), callsign_color, theme.FONT_SIZE_SMALL)]
        if self.show_altitude_labels:
            alt = _short_altitude(ac)
            if alt:
                lines.append((alt, color, theme.FONT_SIZE_TINY))
        return tuple(lines)

    @staticmethod
    def _glow_level(pos: tuple[float, float], sweep_angle: float) -> int:
        """Aircraft flare up as the sweep passes over them, then settle."""
        cx, cy = theme.SCREEN_CENTER
        bearing = math.degrees(math.atan2(pos[0] - cx, cy - pos[1])) % 360
        behind = (sweep_angle - bearing) % 360
        if behind > theme.SWEEP_HIGHLIGHT_DEG:
            return 1
        boost = 1 - behind / theme.SWEEP_HIGHLIGHT_DEG
        return 1 + round(boost * (gfx.GLOW_LEVELS - 2))

    def _draw_status_card(
        self, surface: pygame.Surface, title: str, detail: str, color: tuple[int, int, int]
    ) -> None:
        width, height = 320, 92
        card = gfx.panel(width, height)
        rect = card.get_rect(center=(theme.SCREEN_CENTER[0], theme.SCREEN_CENTER[1] + 90))
        surface.blit(card, rect)
        gfx.blit_text(
            surface, title, theme.FONT_SIZE_SMALL, color, "semibold", theme.TRACKING_LABEL,
            center=(rect.centerx, rect.top + 34),
        )
        gfx.blit_text(
            surface, detail, theme.FONT_SIZE_SMALL, theme.TEXT_SECONDARY,
            center=(rect.centerx, rect.top + 62),
        )


def _short_altitude(ac: Aircraft) -> str | None:
    """Compact data-block altitude, e.g. '35.0k ↑' or 'GND'."""
    if ac.is_ground():
        return "GND"
    alt = ac.altitude_ft()
    if alt is None:
        return None
    text = f"{alt / 1000:.1f}k"
    if ac.vertical_rate is not None and abs(ac.vertical_rate) >= VERTICAL_TREND_FPM:
        text += " ↑" if ac.vertical_rate > 0 else " ↓"
    return text
