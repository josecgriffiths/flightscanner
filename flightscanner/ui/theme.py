"""Centralised visual constants for FLIGHTSCANNER.

Nothing outside this module should hard-code colours, font sizes, or
layout constants. The visual language is a modern glass-cockpit look
designed for a round 720x720 panel: deep blue-black backdrop, soft teal
accent, aircraft coloured by altitude, and everything laid out in
concentric bands around the centre of the screen.

Radial layout (distance from screen centre, px):

    0 ............ 300   radar scope (aircraft, rings, sweep)
    300 .......... 314   bearing tick marks
    314 .......... 330   compass letters N / E / S / W
    326 .......... 352   curved bezel text, page dots, altitude legend
    352 .......... 360   physical edge of the round panel -- keep clear
"""
from __future__ import annotations

# --- Screen geometry -------------------------------------------------
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 720
SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
SCREEN_RADIUS = 360
SAFE_RADIUS = 352  # nothing is drawn beyond this radius (round panel edge)

# --- Colours -----------------------------------------------------------
BACKGROUND = (3, 5, 9)  # outside the scope / panel edge
SCOPE_CENTER = (12, 22, 30)  # radial gradient: centre of the scope...
SCOPE_EDGE = (5, 9, 14)  # ...fading to this at the outer ring
GRID_LINE = (44, 70, 78)
GRID_LINE_FAINT = (22, 36, 42)
TICK_MAJOR = (70, 104, 112)
TICK_MINOR = (30, 46, 52)
TEXT_PRIMARY = (232, 240, 242)
TEXT_SECONDARY = (160, 176, 182)
TEXT_MUTED = (96, 114, 122)
ACCENT = (64, 224, 196)
ACCENT_DIM = (30, 104, 94)
WARNING = (255, 176, 64)
ALERT = (255, 78, 88)
RECEIVER_MARKER = ACCENT
AIRCRAFT_UNKNOWN_ALT = (210, 220, 224)  # no altitude reported
AIRCRAFT_GROUND = (120, 132, 138)
SELECTION = (255, 255, 255)

# Panels / cards: translucent fill over the scope, hairline border.
PANEL_FILL = (10, 18, 26, 240)  # RGBA
PANEL_BORDER = (52, 84, 94)
PANEL_RADIUS = 18

# --- Altitude colour scale ---------------------------------------------
# (altitude ft, colour) stops, interpolated linearly. Warm = low, cool = high.
ALTITUDE_STOPS = [
    (0, (255, 128, 64)),
    (4_000, (255, 196, 72)),
    (10_000, (148, 232, 96)),
    (20_000, (56, 222, 196)),
    (30_000, (72, 168, 255)),
    (40_000, (176, 128, 255)),
]
ALTITUDE_COLOR_STEP_FT = 500  # quantise so sprite caches stay small


def altitude_color(altitude_ft: float | None, on_ground: bool = False) -> tuple[int, int, int]:
    """Map an altitude to its colour on the ALTITUDE_STOPS scale."""
    if on_ground:
        return AIRCRAFT_GROUND
    if altitude_ft is None:
        return AIRCRAFT_UNKNOWN_ALT

    alt = round(altitude_ft / ALTITUDE_COLOR_STEP_FT) * ALTITUDE_COLOR_STEP_FT
    if alt <= ALTITUDE_STOPS[0][0]:
        return ALTITUDE_STOPS[0][1]
    for (a0, c0), (a1, c1) in zip(ALTITUDE_STOPS, ALTITUDE_STOPS[1:]):
        if alt <= a1:
            t = (alt - a0) / (a1 - a0)
            return mix(c0, c1, t)
    return ALTITUDE_STOPS[-1][1]


def mix(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, int, int]:
    """Linear blend from colour a (t=0) to colour b (t=1)."""
    t = max(0.0, min(1.0, t))
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


# --- Fonts -------------------------------------------------------------
# Bundled in flightscanner/assets/fonts (SIL Open Font License). If a file
# is missing the UI falls back to pygame's default font rather than crash.
FONT_FILES = {
    "light": "Inter-Light.ttf",
    "regular": "Inter-Regular.ttf",
    "medium": "Inter-Medium.ttf",
    "semibold": "Inter-SemiBold.ttf",
    "mono": "JetBrainsMono-Medium.ttf",  # numbers / callsigns: fixed width, no jitter
    "mono_bold": "JetBrainsMono-Bold.ttf",
}

FONT_SIZE_DISPLAY = 84  # weather temperature
FONT_SIZE_HEADING = 30
FONT_SIZE_VALUE = 26
FONT_SIZE_NORMAL = 20
FONT_SIZE_SMALL = 15
FONT_SIZE_TINY = 12
FONT_SIZE_MICRO = 10

TRACKING_LABEL = 2  # extra letter spacing (px) for small uppercase labels

# --- Line widths / margins ---------------------------------------------
LINE_WIDTH_THIN = 1
LINE_WIDTH_NORMAL = 2
MARGIN = 16

# --- Bezel layout (radii from screen centre) ----------------------------
TICK_INNER_RADIUS = 302
TICK_MINOR_LENGTH = 4
TICK_MAJOR_LENGTH = 9
TICK_CARDINAL_LENGTH = 12
COMPASS_LABEL_RADIUS = 323
BEZEL_TEXT_RADIUS = 336
BEZEL_TEXT_OUTER_RADIUS = 345
PAGE_DOT_RADIUS = 343

# Angles (degrees clockwise from north) where bezel content is centred.
BEZEL_BRAND_ANGLE = -40
BEZEL_CLOCK_ANGLE = 40
BEZEL_COUNT_ANGLE = 220
BEZEL_LEGEND_START = 118
BEZEL_LEGEND_END = 152
PAGE_DOT_SPACING_DEG = 4.5

# --- Aircraft -----------------------------------------------------------
AIRCRAFT_SYMBOL_SIZE = 22  # sprite edge length in px
AIRCRAFT_TOUCH_RADIUS = 30
TRAIL_SAMPLE_SECONDS = 2.0
TRAIL_LENGTH = 30  # samples kept per aircraft (~1 minute)
GLOW_SIZE = 44

# --- Radar --------------------------------------------------------------
RADAR_RADIUS_PX = 300
RANGE_RING_STEPS = 4  # number of concentric rings including outer edge
RANGE_LABEL_BEARING = 112  # degrees; where ring distance labels sit
SWEEP_PERIOD_SECONDS = 5.0
SWEEP_TRAIL_DEG = 70
SWEEP_MAX_ALPHA = 54
SWEEP_HIGHLIGHT_DEG = 50  # aircraft glow brighter for this long after the sweep passes

# --- Detail card --------------------------------------------------------
DETAIL_CARD_WIDTH = 360
DETAIL_CARD_HEIGHT = 180
DETAIL_CARD_OFFSET = 70  # gap between screen centre and the card's near edge

# --- Animation ----------------------------------------------------------
ALERT_FLASH_HZ = 2.0  # pulses per second for the overhead-aircraft alert
PAGE_FADE_SECONDS = 0.22
