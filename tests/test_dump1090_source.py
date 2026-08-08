import json

from flightscanner.adsb.dump1090 import Dump1090Source


def test_missing_file_returns_empty_and_offline(tmp_path):
    source = Dump1090Source(tmp_path / "does_not_exist.json")
    assert source.get_aircraft() == []
    assert source.status() == "OFFLINE"


def test_valid_file_is_parsed(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({
        "now": 123.0,
        "aircraft": [
            {"hex": "406abc", "flight": "BAW123 ", "lat": 51.1, "lon": -0.1, "alt_baro": 32000},
            {"hex": "abcdef"},
        ],
    }))
    source = Dump1090Source(path)
    aircraft = source.get_aircraft()
    assert len(aircraft) == 2
    assert source.status() == "LIVE"
    assert {a.icao for a in aircraft} == {"406abc", "abcdef"}


def test_empty_aircraft_list_is_valid(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"now": 1.0, "aircraft": []}))
    source = Dump1090Source(path)
    assert source.get_aircraft() == []
    assert source.status() == "LIVE"


def test_malformed_json_falls_back_to_empty_when_no_prior_snapshot(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text("{not valid json")
    source = Dump1090Source(path)
    assert source.get_aircraft() == []
    assert source.status() == "OFFLINE"


def test_malformed_json_keeps_last_good_snapshot_within_grace_period(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"aircraft": [{"hex": "406abc"}]}))
    source = Dump1090Source(path, stale_grace_seconds=100.0)

    first = source.get_aircraft()
    assert len(first) == 1

    path.write_text("{not valid json")
    second = source.get_aircraft()
    assert second == first  # retained, not cleared
    assert source.status() == "LIVE"


def test_missing_aircraft_key_treated_as_read_failure(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"now": 1.0}))
    source = Dump1090Source(path)
    assert source.get_aircraft() == []
    assert source.status() == "OFFLINE"


def test_aircraft_value_not_a_list_treated_as_read_failure(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"aircraft": "oops"}))
    source = Dump1090Source(path)
    assert source.get_aircraft() == []


def test_root_not_an_object_treated_as_read_failure(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps([1, 2, 3]))
    source = Dump1090Source(path)
    assert source.get_aircraft() == []


def test_non_dict_entries_in_aircraft_list_are_skipped(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"aircraft": ["not-a-dict", {"hex": "406abc"}]}))
    source = Dump1090Source(path)
    aircraft = source.get_aircraft()
    assert len(aircraft) == 1
    assert aircraft[0].icao == "406abc"


def test_entries_missing_hex_are_skipped(tmp_path):
    path = tmp_path / "aircraft.json"
    path.write_text(json.dumps({"aircraft": [{"flight": "NO_HEX"}, {"hex": "406abc"}]}))
    source = Dump1090Source(path)
    aircraft = source.get_aircraft()
    assert len(aircraft) == 1
