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
from flightscanner.ui import gfx, navigation, theme, widgets
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
        self._display_size = (config.display.width, config.display.height)
        self._display_flags = pygame.FULLSCREEN if fullscreen else 0
        pygame.display.set_mode(self._display_size, self._display_flags)
        # everything draws to this off-screen frame; _present() copies it to the window
        self.screen = pygame.Surface(self._display_size).convert()
        self._present_failures = 0
        self.clock = pygame.time.Clock()
        self.input_handler = InputHandler()
        self._fade_from: pygame.Surface | None = None  # last frame of the previous page
        self._fade_start = 0.0
        self._plain_backdrop: pygame.Surface | None = None

        self.source = self._build_source(scenario)
        self.radar_page = RadarPage(
            config.receiver.latitude, config.receiver.longitude, config.radar.range_nm,
            config.radar.proximity_alert_nm, config.radar.show_altitude_labels,
            config.display.effects,
        )
        receiver_page.configure(config.data.stats_path)
        weather_page.configure(
            config.receiver.latitude, config.receiver.longitude,
            config.weather.enabled, config.weather.refresh_minutes,
        )
        news_page.configure(config.news.enabled, config.news.feed_url, config.news.refresh_minutes)

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
            self._go_to(navigation.previous_page(self.current_page))
        elif key == pygame.K_RIGHT:
            self._go_to(navigation.next_page(self.current_page))

    def _handle_gesture(self, gesture) -> None:
        if gesture.type == GestureType.SWIPE_LEFT:
            self._go_to(navigation.next_page(self.current_page))
        elif gesture.type == GestureType.SWIPE_RIGHT:
            self._go_to(navigation.previous_page(self.current_page))
        elif gesture.type == GestureType.TAP:
            if self.current_page == navigation.Page.RADAR:
                self.radar_page.handle_tap((gesture.x, gesture.y))

    def _go_to(self, page: navigation.Page) -> None:
        """Switch page, cross-fading from a snapshot of the current frame."""
        if page == self.current_page:
            return
        self._fade_from = self.screen.copy()
        self._fade_start = time.monotonic()
        self.current_page = page

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
        if self.current_page != navigation.Page.RADAR:
            self.screen.blit(self._page_backdrop(), (0, 0))

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

        self._draw_bezel()
        navigation.draw_page_indicator(self.screen, self.current_page)
        self._draw_page_fade()

        if self.debug_enabled:
            self._draw_debug()

        self._present()

    def _present(self) -> None:
        """Copy the finished frame to the window and flip.

        Under Wayland, SDL occasionally reports the window surface as locked
        for a frame. Drawing to an off-screen frame means only this one blit
        can hit that, so the frame is skipped instead of crashing the app.
        If it persists, the window surface is rebuilt.
        """
        window = pygame.display.get_surface()
        try:
            window.blit(self.screen, (0, 0))
        except pygame.error as exc:
            self._present_failures += 1
            if self._present_failures == 1 or self._present_failures % 30 == 0:
                logger.warning(
                    "Skipped frame (%d in a row): %s; window locked=%s size=%s",
                    self._present_failures, exc, window.get_locked(), window.get_size(),
                )
            if self._present_failures >= 30:
                logger.warning("Rebuilding the window surface")
                pygame.display.set_mode(self._display_size, self._display_flags)
                self._present_failures = 0
            return
        self._present_failures = 0
        pygame.display.flip()

    def _page_backdrop(self) -> pygame.Surface:
        """Plain scope gradient (no rings) used behind the non-radar pages."""
        if self._plain_backdrop is None:
            self._plain_backdrop = widgets.build_page_backdrop()
        return self._plain_backdrop

    def _draw_bezel(self) -> None:
        """Curved branding and clock along the top of the round bezel."""
        gfx.arc_text(
            self.screen, BRANDING_TEXT, theme.FONT_SIZE_SMALL, theme.TEXT_SECONDARY,
            theme.BEZEL_TEXT_OUTER_RADIUS - 2, theme.BEZEL_BRAND_ANGLE, tracking=3,
        )
        gfx.arc_text(
            self.screen, STUDIO_TEXT, theme.FONT_SIZE_MICRO, theme.TEXT_MUTED,
            theme.BEZEL_TEXT_RADIUS - 8, theme.BEZEL_BRAND_ANGLE, tracking=2,
        )
        gfx.arc_text(
            self.screen, time.strftime("%H:%M"), theme.FONT_SIZE_SMALL, theme.TEXT_SECONDARY,
            theme.BEZEL_TEXT_RADIUS + 4, theme.BEZEL_CLOCK_ANGLE, role="mono", tracking=1,
        )

    def _draw_page_fade(self) -> None:
        if self._fade_from is None:
            return
        t = (time.monotonic() - self._fade_start) / theme.PAGE_FADE_SECONDS
        if t >= 1.0:
            self._fade_from = None
            return
        self._fade_from.set_alpha(round(255 * (1 - t) ** 2))
        self.screen.blit(self._fade_from, (0, 0))

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
