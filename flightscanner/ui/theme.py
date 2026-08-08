"""Centralised visual constants for FLIGHTSCANNER.

Nothing outside this module should hard-code colours, font sizes, or
layout constants. The visual language is a restrained aviation-instrument
look: near-black background, muted grid, high-contrast symbols.
"""
from __future__ import annotations

# --- Screen geometry -------------------------------------------------
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 720
SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
SCREEN_RADIUS = 360
SAFE_RADIUS = 315  # keep important content inside this radius

# --- Colours -----------------------------------------------------------
BACKGROUND = (6, 8, 10)
GRID_LINE = (32, 45, 40)
GRID_LINE_FAINT = (20, 28, 26)
TEXT_PRIMARY = (225, 230, 228)
TEXT_MUTED = (120, 132, 128)
ACCENT = (80, 200, 160)
WARNING = (220, 120, 70)
AIRCRAFT_SYMBOL = (225, 230, 228)
AIRCRAFT_STALE = (110, 118, 116)
AIRCRAFT_SELECTED = ACCENT
RECEIVER_MARKER = (90, 160, 150)

# --- Fonts (sizes in px, actual Font objects built lazily) -------------
FONT_NAME = None  # pygame default font
FONT_SIZE_HEADING = 40
FONT_SIZE_VALUE = 34
FONT_SIZE_NORMAL = 24
FONT_SIZE_SMALL = 18
FONT_SIZE_TINY = 13

# --- Line widths / margins ---------------------------------------------
LINE_WIDTH_THIN = 1
LINE_WIDTH_NORMAL = 2
MARGIN = 16

# --- Touch targets -------------------------------------------------------
AIRCRAFT_SYMBOL_SIZE = 14
AIRCRAFT_TOUCH_RADIUS = 30

# --- Radar defaults ------------------------------------------------------
RADAR_RADIUS_PX = 300
RANGE_RING_STEPS = 4  # number of concentric rings including outer edge
