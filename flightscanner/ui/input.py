"""Input abstraction turning raw Pygame mouse/touch events into logical
gestures (TAP, SWIPE_LEFT, SWIPE_RIGHT) that the rest of the app consumes.

Mouse (Mac dev) and finger/touch (Pi) events are normalised to the same
logical event so page/selection code never has to know which was used.
SDL can emit both a finger and a synthesised mouse event for one physical
touch; we only track one active pointer at a time to avoid double firing.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto

import pygame

SWIPE_MIN_DISTANCE_PX = 80
SWIPE_VERTICAL_RATIO = 0.6  # horizontal move must exceed vertical * this


class GestureType(Enum):
    TAP = auto()
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()


@dataclass
class Gesture:
    type: GestureType
    x: float = 0.0
    y: float = 0.0


class InputHandler:
    """Feed pygame events in; get logical Gesture objects out."""

    def __init__(self) -> None:
        self._down_pos: tuple[float, float] | None = None
        self._down_time: float = 0.0
        self._pointer_active_source: str | None = None  # "mouse" or "touch"

    def handle_event(self, event: pygame.event.Event, screen_size: tuple[int, int]) -> Gesture | None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._pointer_active_source is None:
                self._pointer_active_source = "mouse"
                self._down_pos = event.pos
                self._down_time = time.monotonic()
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pointer_active_source == "mouse":
                self._pointer_active_source = None
                return self._resolve(event.pos)
            return None

        if event.type == pygame.FINGERDOWN:
            if self._pointer_active_source is None:
                self._pointer_active_source = "touch"
                self._down_pos = (event.x * screen_size[0], event.y * screen_size[1])
                self._down_time = time.monotonic()
            return None

        if event.type == pygame.FINGERUP:
            if self._pointer_active_source == "touch":
                self._pointer_active_source = None
                pos = (event.x * screen_size[0], event.y * screen_size[1])
                return self._resolve(pos)
            return None

        return None

    def _resolve(self, up_pos: tuple[float, float]) -> Gesture | None:
        if self._down_pos is None:
            return None
        dx = up_pos[0] - self._down_pos[0]
        dy = up_pos[1] - self._down_pos[1]
        down_pos = self._down_pos
        self._down_pos = None

        if abs(dx) >= SWIPE_MIN_DISTANCE_PX and abs(dx) > abs(dy) * (1 / SWIPE_VERTICAL_RATIO):
            return Gesture(GestureType.SWIPE_RIGHT if dx > 0 else GestureType.SWIPE_LEFT)

        return Gesture(GestureType.TAP, x=down_pos[0], y=down_pos[1])
