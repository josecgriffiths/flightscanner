from pathlib import Path

from flightscanner.config import load_config


def test_load_config_missing_path_uses_defaults(tmp_path):
    cfg = load_config(tmp_path / "does_not_exist.toml")
    assert cfg.display.width == 720
    assert cfg.display.height == 720
    assert cfg.receiver.latitude is None


def test_load_config_none_path_uses_defaults():
    cfg = load_config(None)
    assert cfg.radar.range_nm == 50.0


def test_load_config_reads_values(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[receiver]
latitude = 40.0
longitude = -3.0

[radar]
range_nm = 25
"""
    )
    cfg = load_config(config_file)
    assert cfg.receiver.latitude == 40.0
    assert cfg.receiver.longitude == -3.0
    assert cfg.radar.range_nm == 25
    # unspecified sections still fall back to defaults
    assert cfg.display.fps == 30
