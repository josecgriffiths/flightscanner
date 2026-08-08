from flightscanner.adsb.models import Aircraft, aircraft_from_dump1090, normalise_callsign


def test_callsign_trimming():
    assert normalise_callsign("BAW123 ") == "BAW123"
    assert normalise_callsign("  ") is None
    assert normalise_callsign(None) is None


def test_display_callsign_falls_back_to_icao():
    ac = Aircraft(icao="406abc", callsign=None)
    assert ac.display_callsign() == "406ABC"


def test_display_callsign_uses_trimmed_callsign():
    ac = Aircraft(icao="406abc", callsign="BAW123 ")
    assert ac.display_callsign() == "BAW123"


def test_missing_position():
    ac = Aircraft(icao="406abc")
    assert ac.has_position() is False


def test_has_position_true():
    ac = Aircraft(icao="406abc", latitude=51.0, longitude=-0.1)
    assert ac.has_position() is True


def test_ground_altitude_display():
    ac = Aircraft(icao="406abc", altitude_baro="ground")
    assert ac.is_ground() is True
    assert ac.display_altitude() == "GROUND"


def test_missing_altitude_display():
    ac = Aircraft(icao="406abc")
    assert ac.display_altitude() is None


def test_aircraft_from_dump1090_basic():
    entry = {
        "hex": "406ABC",
        "flight": "BAW123 ",
        "alt_baro": 32000,
        "gs": 453.2,
        "track": 274.0,
        "lat": 52.123,
        "lon": -1.234,
    }
    ac = aircraft_from_dump1090(entry)
    assert ac is not None
    assert ac.icao == "406abc"
    assert ac.callsign == "BAW123"
    assert ac.altitude_baro == 32000
    assert ac.has_position()


def test_aircraft_from_dump1090_missing_hex_returns_none():
    assert aircraft_from_dump1090({"flight": "BAW123"}) is None


def test_aircraft_from_dump1090_missing_optional_fields():
    ac = aircraft_from_dump1090({"hex": "abc123"})
    assert ac is not None
    assert ac.callsign is None
    assert ac.has_position() is False
    assert ac.display_speed() is None
    assert ac.display_track() is None


def test_is_stale():
    assert Aircraft(icao="a", seen=45.0).is_stale() is True
    assert Aircraft(icao="a", seen=5.0).is_stale() is False
    assert Aircraft(icao="a", seen=None).is_stale() is False
