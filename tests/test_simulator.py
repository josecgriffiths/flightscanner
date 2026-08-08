import pytest

from flightscanner.adsb.simulator import SimulatorSource


def test_simulator_produces_configured_count():
    sim = SimulatorSource(receiver_lat=51.5, receiver_lon=-0.12, count=12, seed=1)
    aircraft = sim.get_aircraft()
    assert len(aircraft) == 12


def test_simulator_aircraft_have_positions():
    sim = SimulatorSource(receiver_lat=51.5, receiver_lon=-0.12, count=5, seed=1)
    for ac in sim.get_aircraft():
        assert ac.has_position()
        assert ac.callsign is not None
        assert ac.icao


def test_simulator_deterministic_with_same_seed():
    sim1 = SimulatorSource(receiver_lat=51.5, receiver_lon=-0.12, count=5, seed=99)
    sim2 = SimulatorSource(receiver_lat=51.5, receiver_lon=-0.12, count=5, seed=99)
    ac1 = sim1.get_aircraft()
    ac2 = sim2.get_aircraft()
    assert [a.icao for a in ac1] == [a.icao for a in ac2]
    for a, b in zip(ac1, ac2):
        assert a.latitude == pytest.approx(b.latitude, abs=1e-6)
        assert a.longitude == pytest.approx(b.longitude, abs=1e-6)


def test_simulator_status_is_demo():
    sim = SimulatorSource(receiver_lat=51.5, receiver_lon=-0.12, count=1, seed=1)
    assert sim.status() == "DEMO"
