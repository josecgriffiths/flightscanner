"""Tests for tolerant parsing of dump1090-style aircraft.json payloads.

These exercise aircraft_from_dump1090 directly against malformed/partial
data shapes. File-level read failures (missing file, torn JSON, etc.)
are covered separately in test_dump1090_source.py.
"""
from flightscanner.adsb.models import aircraft_from_dump1090


def test_empty_aircraft_list_is_fine():
    payload = {"now": 123.0, "aircraft": []}
    parsed = [aircraft_from_dump1090(e) for e in payload["aircraft"]]
    assert parsed == []


def test_missing_aircraft_key_handled_by_caller():
    payload = {"now": 123.0}
    aircraft_list = payload.get("aircraft", [])
    assert aircraft_list == []


def test_entry_missing_hex_is_skipped():
    entries = [{"flight": "BAW1"}, {"hex": "abc123"}]
    parsed = [aircraft_from_dump1090(e) for e in entries]
    parsed = [a for a in parsed if a is not None]
    assert len(parsed) == 1
    assert parsed[0].icao == "abc123"


def test_entry_with_partial_fields_does_not_raise():
    entry = {"hex": "abc123", "seen": 0.4}
    ac = aircraft_from_dump1090(entry)
    assert ac is not None
    assert ac.display_speed() is None
    assert ac.display_altitude() is None
