import _bootstrap  # noqa: F401

import json


ROOT = _bootstrap.ROOT


def _load(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_m4_16gb_preset_matches_config_example():
    # config-example.json is tuned for the 16 GB M4; its preset must stay in sync.
    preset = _load("m4-16gb-preset.json")
    example = _load("config-example.json")

    assert "app" not in preset  # Import Config ignores the app section
    for section, values in preset.items():
        for key, value in values.items():
            assert example[section][key] == value, f"{section}.{key}"


def test_m4_pro_preset_uses_known_keys_and_more_memory():
    pro = _load("m4-pro-24gb-preset.json")
    base = _load("m4-16gb-preset.json")
    example = _load("config-example.json")

    assert "app" not in pro
    assert {s: set(v) for s, v in pro.items()} == {s: set(v) for s, v in base.items()}
    for section, values in pro.items():
        for key in values:
            assert key in example[section], f"{section}.{key}"
    assert pro["inpainter"]["inpainting_size"] > base["inpainter"]["inpainting_size"]
    assert pro["cli"]["batch_size"] > base["cli"]["batch_size"]
