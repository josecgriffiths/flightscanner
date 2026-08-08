"""Main application: owns the Pygame loop, page state, and data polling.

Rendering runs at a fixed target FPS; the aircraft source is polled at a
much lower frequency using wall-clock gating rather than a background
thread, since polling from the main loop is simpler to reason about and
plenty fast enough at 1-2 Hz.
"""
from __future__ import annotations

import logging
import time

import pygame

from flightscanner.adsb.dump1090 import Dump1090Source
from flightscanner.adsb.simulator import SimulatorSource
from flightscanner.config import Config
from flightscanner.pages import news_page, receiver_page, system_page, weather_page
from flightscanner.pages.radar_page import RadarPage
from flightscanner.ui import debug as debug_ui
from flightscanner.ui import navigation, theme
from flightscanner.ui.input import GestureType, InputHandler

logger = logging.getLogger(__name__)

BRANDING_TEXT = "FLIGHTSCANNER"
STUDIO_TEXT = "BARE METAL STUDIO"


class App:
    def __init__(self, config: Config, mode: str, fullscreen: bool, debug: bool, scenario: str | None) -> None:
        self.config = config
        self.mode = mode  # "demo" or "live"
        self.debug_enabled = debug
        self.current_page = navigation.Page.RADAR
        self.running = True

        pygame.init()
        pygame.display.set_caption(f"{BRANDING_TEXT} - {STUDIO_TEXT}")
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode(
            (config.display.width, config.display.height), flags
        )
        self.clock = pygame.time.Clock()
        self.input_handler = InputHandler()
        self._branding_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_SMALL)
        self._studio_font = pygame.font.Font(theme.FONT_NAME, theme.FONT_SIZE_TINY)

        self.source = self._build_source(scenario)
        self.radar_page = RadarPage(
            config.receiver.latitude, config.receiver.longitude, config.radar.range_nm
        )

        self._next_data_poll = 0.0
        self._data_poll_interval = 1.0 / max(config.data.refresh_hz, 0.1)
        self._last_aircraft: list = []
        self._last_read_ok_time: float | None = None
        self._fps_display = 0.0

    def _build_source(self, scenario: str | None):
        if self.mode == "demo":
            count = self.config.demo.aircraft_count
            if scenario == "busy":
                count = max(count, 25)
            elif scenario == "sparse":
                count = max(3, count // 3)
            lat = self.config.receiver.latitude if self.config.receiver.latitude is not None else 51.5
            lon = self.config.receiver.longitude if self.config.receiver.longitude is not None else -0.12
            return SimulatorSource(
                receiver_lat=lat,
                receiver_lon=lon,
                count=count,
                seed=self.config.demo.seed,
                radar_range_nm=self.config.radar.range_nm,
            )

        return Dump1090Source(self.config.data.dump1090_path)

    def run(self) -> None:
        try:
            while self.running:
                self._handle_events()
                self._poll_data()
                self._render()
                self._fps_display = self.clock.get_fps()
                self.clock.tick(self.config.display.fps)
        finally:
            pygame.quit()

    def _handle_events(self) -> None:
        screen_size = (self.config.display.width, self.config.display.height)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            if event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
                continue

            gesture = self.input_handler.handle_event(event, screen_size)
            if gesture is not None:
                self._handle_gesture(gesture)

    def _handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_d:
            self.debug_enabled = not self.debug_enabled
        elif key == pygame.K_f:
            pygame.display.toggle_fullscreen()
        elif key == pygame.K_LEFT:
            self.current_page = navigation.previous_page(self.current_page)
        elif key == pygame.K_RIGHT:
            self.current_page = navigation.next_page(self.current_page)

    def _handle_gesture(self, gesture) -> None:
        if gesture.type == GestureType.SWIPE_LEFT:
            self.current_page = navigation.next_page(self.current_page)
        elif gesture.type == GestureType.SWIPE_RIGHT:
            self.current_page = navigation.previous_page(self.current_page)
        elif gesture.type == GestureType.TAP:
            if self.current_page == navigation.Page.RADAR:
                self.radar_page.handle_tap((gesture.x, gesture.y))

    def _poll_data(self) -> None:
        now = time.monotonic()
        if now < self._next_data_poll:
            return
        self._next_data_poll = now + self._data_poll_interval
        try:
            self._last_aircraft = self.source.get_aircraft()
            self._last_read_ok_time = now
        except Exception:
            logger.exception("Failed to read aircraft data; keeping last known snapshot")

    def _render(self) -> None:
        self.screen.fill(theme.BACKGROUND)

        receiver_online = self.source.status() != "OFFLINE"

        if self.current_page == navigation.Page.RADAR:
            self.radar_page.update_and_draw(self.screen, self._last_aircraft, receiver_online)
        elif self.current_page == navigation.Page.RECEIVER:
            receiver_page.draw(self.screen)
        elif self.current_page == navigation.Page.SYSTEM:
            system_page.draw(self.screen)
        elif self.current_page == navigation.Page.WEATHER:
            weather_page.draw(self.screen)
        elif self.current_page == navigation.Page.NEWS:
            news_page.draw(self.screen)

        self._draw_branding()
        navigation.draw_page_indicator(self.screen, self.current_page)

        if self.debug_enabled:
            self._draw_debug()

        pygame.display.flip()

    def _draw_branding(self) -> None:
        surf = self._branding_font.render(BRANDING_TEXT, True, theme.TEXT_MUTED)
        rect = surf.get_rect()
        rect.topleft = (theme.MARGIN, theme.MARGIN)
        self.screen.blit(surf, rect)

        studio_surf = self._studio_font.render(STUDIO_TEXT, True, theme.GRID_LINE)
        studio_rect = studio_surf.get_rect()
        studio_rect.topleft = (theme.MARGIN, rect.bottom + 2)
        self.screen.blit(studio_surf, studio_rect)

    def _draw_debug(self) -> None:
        # placed below the branding text (top-left) to avoid overlap
        pointer = pygame.mouse.get_pos()
        age = time.monotonic() - self._last_read_ok_time if self._last_read_ok_time else None
        info = debug_ui.DebugInfo(
            fps=self._fps_display,
            mode=self.mode.upper(),
            source_aircraft_count=len(self._last_aircraft),
            rendered_aircraft_count=len(self.radar_page._last_positions),
            selected_icao=self.radar_page.selected_icao,
            radar_range_nm=self.config.radar.range_nm,
            pointer_pos=pointer,
            last_read_ok_age_s=age,
            current_page=self.current_page.name,
        )
        debug_ui.draw_debug_overlay(self.screen, info)
