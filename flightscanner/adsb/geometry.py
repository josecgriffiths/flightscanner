"""Pure geographic and radar-projection maths.

No Pygame, no I/O -- this module is deliberately standalone so it can be
unit tested without a display and eventually ported to another language.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_000.0
METRES_PER_NM = 1852.0


@dataclass(frozen=True)
class PolarPosition:
    """An aircraft's position relative to the receiver."""

    distance_nm: float
    bearing_deg: float  # 0 = North, 90 = East, 180 = South, 270 = West


def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in nautical miles.

    Uses the haversine formula on a spherical Earth of mean radius
    EARTH_RADIUS_M. Adequate for radar-range distances (tens to a few
    hundred nautical miles); it is not geodetically exact.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_m = EARTH_RADIUS_M * c
    return distance_m / METRES_PER_NM


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing from point 1 to point 2, in degrees.

    0 = North, 90 = East, 180 = South, 270 = West. Result is normalised
    to [0, 360).
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        dlambda
    )
    bearing = math.degrees(math.atan2(x, y))
    return bearing % 360.0


def polar_position(
    receiver_lat: float, receiver_lon: float, lat: float, lon: float
) -> PolarPosition:
    """Compute distance + bearing of (lat, lon) relative to the receiver."""
    distance = haversine_distance_nm(receiver_lat, receiver_lon, lat, lon)
    bearing = initial_bearing_deg(receiver_lat, receiver_lon, lat, lon)
    return PolarPosition(distance_nm=distance, bearing_deg=bearing)


def project_to_radar(
    distance_nm: float,
    bearing_deg: float,
    center: tuple[float, float],
    radar_range_nm: float,
    radar_radius_px: float,
) -> tuple[float, float]:
    """Project a polar (distance, bearing) position onto radar screen pixels.

    Screen Y grows downward, so North (bearing 0) must move *up* the
    screen -- hence the minus sign on the Y term.
    """
    pixel_radius = (distance_nm / radar_range_nm) * radar_radius_px
    bearing_rad = math.radians(bearing_deg)

    cx, cy = center
    x = cx + pixel_radius * math.sin(bearing_rad)
    y = cy - pixel_radius * math.cos(bearing_rad)
    return x, y


def point_inside_safe_circle(
    point: tuple[float, float], center: tuple[float, float], safe_radius: float
) -> bool:
    """True if point lies within safe_radius of center."""
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    return (dx * dx + dy * dy) <= safe_radius * safe_radius


def rect_inside_safe_circle(rect, center: tuple[float, float], safe_radius: float) -> bool:
    """True if every corner of a pygame.Rect-like object is within safe_radius.

    `rect` only needs .topleft, .topright, .bottomleft, .bottomright
    attributes (a pygame.Rect satisfies this), so this stays Pygame-free.
    """
    corners = [rect.topleft, rect.topright, rect.bottomleft, rect.bottomright]
    return all(point_inside_safe_circle(c, center, safe_radius) for c in corners)
