# FLIGHTSCANNER

A Bare Metal Studio project.

A standalone aircraft radar appliance built for a Raspberry Pi 5 and a
720x720 circular touchscreen. It visualises real ADS-B traffic decoded by
`dump1090-fa`, and runs the exact same code in a simulated **demo mode**
for development on a Mac with no receiver hardware attached.

## What is ADS-B, briefly

Aircraft continuously broadcast their position, altitude, speed and
identity over radio at 1090 MHz (ADS-B). A FlightAware Pro Stick Plus USB
receiver picks up that RF. `dump1090-fa` demodulates and decodes it into
JSON. FlightScanner reads that JSON and draws it on a radar-style display.
FlightScanner never touches the SDR hardware or does any RF/Mode-S
decoding itself.

## Architecture

```
AIRCRAFT (1090 MHz broadcast)
   -> ANTENNA -> FlightAware Pro Stick Plus (USB)
   -> dump1090-fa   (RF -> Mode-S -> ADS-B -> JSON)
   -> /run/dump1090-fa/aircraft.json
   -> FlightScanner AircraftSource        (Dump1090Source | SimulatorSource)
   -> list[Aircraft]                       (shared, source-agnostic model)
   -> geometry (haversine distance/bearing -> radar pixel projection)
   -> Pygame renderer
   -> 720x720 Waveshare circular touchscreen
```

The UI layer never parses dump1090 JSON and never knows whether an
`Aircraft` came from a real receiver or the simulator -- both sides of
that abstraction produce the same `Aircraft` dataclass
(`flightscanner/adsb/models.py`) via the `AircraftSource` protocol
(`flightscanner/adsb/source.py`).

### Package layout

```
flightscanner/
  app.py            main Pygame loop, page/input wiring, data polling
  config.py         TOML config loading (stdlib tomllib)
  logging_setup.py  console + rotating file logging
  adsb/
    models.py        Aircraft dataclass + dump1090 entry parsing
    source.py         AircraftSource protocol
    dump1090.py         Dump1090Source -- reads aircraft.json from disk
    simulator.py          SimulatorSource -- moving fake aircraft for demo mode
    geometry.py             haversine distance/bearing + radar pixel projection
  ui/
    theme.py          all colours/fonts/sizes/screen geometry constants
    radar.py           range rings, crosshair, compass, receiver marker
    aircraft.py         aircraft symbol, label placement, interpolation, hit-testing
    aircraft_details.py  selected-aircraft info panel
    navigation.py         Page enum + swipe dot indicator
    input.py                mouse/touch -> TAP/SWIPE gesture abstraction
    debug.py                  developer overlay (toggle with D)
  pages/
    radar_page.py      the main radar screen
    receiver_page.py, system_page.py, weather_page.py, news_page.py
      -- placeholder screens for later work
  system/
    stats.py           SystemStats dataclass scaffold (not wired up yet)
tests/                pytest suite, no display required
demo/scenarios/        reserved for future scenario data files
deploy/flightscanner.service   systemd unit (not installed automatically)
```

## Development setup (macOS)

Pygame does not yet ship a pre-built wheel for very new Python releases;
use Python 3.11-3.13.

```bash
git clone <repo-url>
cd flightscanner

python3.13 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp config.example.toml config.toml   # demo mode works with the example coords
python main.py --demo
```

### Demo mode

```bash
python main.py --demo
python main.py --demo --scenario busy     # ~25 aircraft
python main.py --demo --scenario sparse   # ~5 aircraft
python main.py --demo --debug             # start with debug overlay on
python main.py --demo --fullscreen
```

### Controls (development)

| Key            | Action                        |
|----------------|--------------------------------|
| ESC            | Quit                           |
| D              | Toggle debug overlay           |
| F              | Toggle fullscreen               |
| LEFT / RIGHT   | Change page                     |
| Mouse click    | Tap gesture (select aircraft, swipe pages by dragging) |

On the physical touchscreen, finger events are translated to the same
TAP/SWIPE_LEFT/SWIPE_RIGHT gestures used by the mouse in development.

### Tests

```bash
pytest
```

Covers Aircraft parsing/normalisation (missing/partial fields, ground
altitude, stale detection), haversine distance and bearing maths, radar
projection for all four cardinal directions, `Dump1090Source` against
missing files, malformed/torn JSON and stale-snapshot retention, config
loading with missing/partial files, and simulator determinism under a
fixed seed.

## Configuration

Configuration is TOML, loaded via the standard library `tomllib`
(`flightscanner/config.py`). Copy `config.example.toml` to `config.toml`
and edit it -- `config.toml` is gitignored so real receiver coordinates
are never committed.

```toml
[receiver]
latitude = 51.5000
longitude = -0.1200

[radar]
range_nm = 50
radius_px = 300
show_altitude_labels = false

[display]
width = 720
height = 720
fullscreen = false
fps = 30

[data]
dump1090_path = "/run/dump1090-fa/aircraft.json"
refresh_hz = 2.0

[demo]
aircraft_count = 15
seed = 42
```

Missing keys/sections fall back to sensible defaults, so a partial or
absent `config.toml` never crashes the app.

## Running on the Raspberry Pi

```bash
ssh adsb@<pi-hostname>
cd ~
git clone <repo-url> flightscanner
cd flightscanner

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.toml config.toml
nano config.toml   # set your real receiver.latitude / receiver.longitude

python main.py --live --fullscreen
```

Deployment workflow:

```
Mac: edit, test, run --demo
  -> git commit / push
Pi:  git pull
  -> systemctl restart flightscanner   (once the service is installed)
```

A systemd unit template is provided at `deploy/flightscanner.service`. It
is **not** installed automatically -- to install it later:

```bash
sudo cp deploy/flightscanner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flightscanner
```

The unit starts after `dump1090-fa.service` and runs as the `adsb` user
from `/home/adsb/flightscanner`.

## Design notes

- **Circular display constraint**: `flightscanner/ui/theme.py` defines
  `SCREEN_RADIUS` (360) and `SAFE_RADIUS` (315). `adsb/geometry.py`
  provides `point_inside_safe_circle` / `rect_inside_safe_circle` helpers
  so important content can be kept off the corners the round bezel hides.
- **No teleporting aircraft**: `ui/aircraft.py`'s `AircraftRenderer` keeps
  previous/target screen positions per ICAO and interpolates between data
  refreshes, snapping instead of gliding for very large jumps (a reseeded
  simulated aircraft, or a receiver restart).
- **Aircraft identity**: selection and interpolation state are keyed by
  ICAO hex, never by object reference, since a new data snapshot always
  produces new `Aircraft` instances.
- **No threads**: the aircraft source is polled from the main loop using
  wall-clock gating (`app.py::_poll_data`), independent of the 30 FPS
  render loop -- simple enough at 1-2 Hz that a background thread isn't
  worth the complexity.
- **Live read resilience**: `Dump1090Source` never raises out of
  `get_aircraft()`. A missing file, torn/invalid JSON, or unexpected
  shapes (root not an object, `aircraft` not a list, non-dict entries,
  entries missing `hex`) are all logged and treated as a failed read.
  The last known-good snapshot is served for `stale_grace_seconds`
  (default 10s) before `status()` reports `OFFLINE`, so a single missed
  read during a file rewrite doesn't blank the radar.

## Known limitations

- Receiver/System/Weather/News pages are still placeholders.
- No label collision solver beyond four candidate offset positions --
  in very dense scenarios some labels may still overlap.
- No systemd installation automation (by design; see above).
- `stats.json` (message rates, receiver uptime, etc.) is not read yet.

## Roadmap

- Wire `/run/dump1090-fa/stats.json` into the RECEIVER STATUS page
  (aircraft tracked, message rate, max range).
- `psutil`-based system metrics on the SYSTEM page, cached at ~1 Hz.
- Weather and news pages (currently placeholders, never a hard
  dependency for the radar itself).
- Longer term: native SDL/DRM rendering, then a C++/Rust renderer, then
  consuming the Beast/raw Mode-S stream directly.

---

Built by Bare Metal Studio.
