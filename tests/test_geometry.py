import math

from flightscanner.adsb.geometry import (
    haversine_distance_nm,
    initial_bearing_deg,
    point_inside_safe_circle,
    project_to_radar,
)

LONDON = (51.5074, -0.1278)


def test_haversine_zero_distance():
    d = haversine_distance_nm(*LONDON, *LONDON)
    assert d == 0.0


def test_haversine_known_roughly():
    # London to Paris is roughly 186 nm great-circle
    paris = (48.8566, 2.3522)
    d = haversine_distance_nm(*LONDON, *paris)
    assert 180 < d < 195


def test_bearing_north():
    lat, lon = LONDON
    bearing = initial_bearing_deg(lat, lon, lat + 1.0, lon)
    assert abs(bearing - 0.0) < 0.5


def test_bearing_east():
    lat, lon = LONDON
    bearing = initial_bearing_deg(lat, lon, lat, lon + 1.0)
    assert abs(bearing - 90.0) < 1.0


def test_bearing_south():
    lat, lon = LONDON
    bearing = initial_bearing_deg(lat, lon, lat - 1.0, lon)
    assert abs(bearing - 180.0) < 0.5


def test_bearing_west():
    lat, lon = LONDON
    bearing = initial_bearing_deg(lat, lon, lat, lon - 1.0)
    assert abs(bearing - 270.0) < 1.0


def test_projection_north_is_above_center():
    center = (360, 360)
    x, y = project_to_radar(25, 0, center, 50, 300)
    assert math.isclose(x, 360, abs_tol=0.5)
    assert y < 360


def test_projection_east_is_right_of_center():
    center = (360, 360)
    x, y = project_to_radar(25, 90, center, 50, 300)
    assert x > 360
    assert math.isclose(y, 360, abs_tol=0.5)


def test_projection_south_is_below_center():
    center = (360, 360)
    x, y = project_to_radar(25, 180, center, 50, 300)
    assert math.isclose(x, 360, abs_tol=0.5)
    assert y > 360


def test_projection_west_is_left_of_center():
    center = (360, 360)
    x, y = project_to_radar(25, 270, center, 50, 300)
    assert x < 360
    assert math.isclose(y, 360, abs_tol=0.5)


def test_projection_at_full_range_reaches_radius():
    center = (0, 0)
    x, y = project_to_radar(50, 90, center, 50, 300)
    assert math.isclose(x, 300, abs_tol=0.5)


class _FakeRect:
    def __init__(self, corners):
        self.topleft, self.topright, self.bottomleft, self.bottomright = corners


def test_point_inside_safe_circle():
    assert point_inside_safe_circle((360, 360), (360, 360), 315) is True
    assert point_inside_safe_circle((360, 360 - 320), (360, 360), 315) is False
