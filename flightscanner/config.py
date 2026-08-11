"""Configuration loading for FLIGHTSCANNER.

Uses TOML (stdlib tomllib) so no extra dependency is required. A committed
config.example.toml documents every field; the real config.toml (with real
receiver coordinates) is gitignored.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReceiverConfig:
    latitude: float | None = None
    longitude: float | None = None


@dataclass
class RadarConfig:
    range_nm: float = 50.0
    radius_px: int = 300
    show_altitude_labels: bool = False


@dataclass
class DisplayConfig:
    width: int = 720
    height: int = 720
    fullscreen: bool = False
    fps: int = 30


@dataclass
class DataConfig:
    dump1090_path: str = "/run/dump1090-fa/aircraft.json"
    stats_path: str = "/run/dump1090-fa/stats.json"
    refresh_hz: float = 2.0


@dataclass
class DemoConfig:
    aircraft_count: int = 15
    seed: int = 42


@dataclass
class WeatherConfig:
    enabled: bool = True
    refresh_minutes: float = 10.0


@dataclass
class NewsConfig:
    enabled: bool = True
    feed_url: str = "https://www.aviation24.be/feed/"
    refresh_minutes: float = 15.0


@dataclass
class Config:
    receiver: ReceiverConfig = field(default_factory=ReceiverConfig)
    radar: RadarConfig = field(default_factory=RadarConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    data: DataConfig = field(default_factory=DataConfig)
    demo: DemoConfig = field(default_factory=DemoConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    news: NewsConfig = field(default_factory=NewsConfig)


def load_config(path: Path | str | None) -> Config:
    """Load configuration from a TOML file, falling back to defaults.

    Missing sections/keys fall back to dataclass defaults so a partial
    config.toml (or none at all) never crashes the application.
    """
    raw: dict = {}
    if path is not None:
        p = Path(path)
        if p.exists():
            with p.open("rb") as f:
                raw = tomllib.load(f)

    return Config(
        receiver=ReceiverConfig(**raw.get("receiver", {})),
        radar=RadarConfig(**raw.get("radar", {})),
        display=DisplayConfig(**raw.get("display", {})),
        data=DataConfig(**raw.get("data", {})),
        demo=DemoConfig(**raw.get("demo", {})),
        weather=WeatherConfig(**raw.get("weather", {})),
        news=NewsConfig(**raw.get("news", {})),
    )


def default_config_path() -> Path:
    """Return the conventional config.toml path relative to the repo root."""
    return Path(__file__).resolve().parent.parent / "config.toml"
