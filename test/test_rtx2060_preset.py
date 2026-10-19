import _bootstrap  # noqa: F401

import json


ROOT = _bootstrap.ROOT


def _load(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_rtx2060_preset_matches_config_example():
    # The shareable preset must stay in sync with the profile's default config.
    preset = _load("rtx2060super-preset.json")
    example = _load("config-example.json")

    assert "app" not in preset  # Import Config ignores the app section
    for section, values in preset.items():
        for key, value in values.items():
            assert example[section][key] == value, f"{section}.{key}"
