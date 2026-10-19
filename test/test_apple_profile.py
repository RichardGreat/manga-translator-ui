import _bootstrap  # noqa: F401

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = _bootstrap.ROOT
GIB = 1024**3


def load_apple_profile():
    spec = importlib.util.spec_from_file_location("apple_profile_test", ROOT / "packaging" / "apple_profile.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ap():
    return load_apple_profile()


@pytest.mark.parametrize(
    "memory_gib, expected",
    [
        (8, "apple-m4-16gb"),
        (16, "apple-m4-16gb"),
        (24, "apple-m4pro-24gb"),
        (36, "apple-m4pro-24gb"),
        (64, "apple-m4pro-24gb"),
    ],
)
def test_select_profile_by_memory(ap, memory_gib, expected):
    assert ap.select_profile(memory_gib * GIB) == expected


def test_deep_merge_overrides_only_listed_keys_without_mutation(ap):
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    overlay = {"a": {"y": 20}}

    merged = ap.deep_merge(base, overlay)

    assert merged == {"a": {"x": 1, "y": 20}, "b": 3}
    assert base == {"a": {"x": 1, "y": 2}, "b": 3}
    assert overlay == {"a": {"y": 20}}


def _write_example(config_dir: Path, data: dict) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config-example.json").write_text(json.dumps(data), encoding="utf-8")


def test_apply_profile_creates_config_from_example_plus_overlay(ap, tmp_path):
    config_dir = tmp_path / "config"
    _write_example(config_dir, {"inpainter": {"inpainting_size": 2048, "inpainter": "lama_large"}, "kernel_size": 3})
    (config_dir / "profiles").mkdir()
    (config_dir / "profiles" / "p.json").write_text(json.dumps({"inpainter": {"inpainting_size": 1024}}), encoding="utf-8")

    status = ap.apply_profile(config_dir, "p")

    assert status == ap.APPLIED
    result = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))
    assert result == {"inpainter": {"inpainting_size": 1024, "inpainter": "lama_large"}, "kernel_size": 3}


def test_apply_profile_never_overwrites_existing_user_config(ap, tmp_path):
    config_dir = tmp_path / "config"
    _write_example(config_dir, {"kernel_size": 3})
    (config_dir / "profiles").mkdir()
    (config_dir / "profiles" / "p.json").write_text(json.dumps({"kernel_size": 9}), encoding="utf-8")
    (config_dir / "config.json").write_text('{"kernel_size": 5}', encoding="utf-8")

    status = ap.apply_profile(config_dir, "p")

    assert status == ap.SKIPPED_EXISTING
    assert json.loads((config_dir / "config.json").read_text(encoding="utf-8")) == {"kernel_size": 5}


def test_apply_profile_force_overwrites_and_keeps_backup(ap, tmp_path):
    config_dir = tmp_path / "config"
    _write_example(config_dir, {"kernel_size": 3})
    (config_dir / "profiles").mkdir()
    (config_dir / "profiles" / "p.json").write_text(json.dumps({"kernel_size": 9}), encoding="utf-8")
    (config_dir / "config.json").write_text('{"kernel_size": 5}', encoding="utf-8")

    status = ap.apply_profile(config_dir, "p", force=True)

    assert status == ap.APPLIED
    assert json.loads((config_dir / "config.json").read_text(encoding="utf-8"))["kernel_size"] == 9
    assert json.loads((config_dir / "config.json.bak").read_text(encoding="utf-8")) == {"kernel_size": 5}


def test_apply_profile_rejects_unknown_profile_name(ap, tmp_path):
    config_dir = tmp_path / "config"
    _write_example(config_dir, {})

    with pytest.raises(FileNotFoundError):
        ap.apply_profile(config_dir, "does-not-exist")


def test_detect_hardware_returns_none_off_apple_silicon(ap, monkeypatch):
    monkeypatch.setattr(ap.platform, "system", lambda: "Linux")
    assert ap.detect_hardware() is None

    monkeypatch.setattr(ap.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(ap.platform, "machine", lambda: "x86_64")
    assert ap.detect_hardware() is None


def test_detect_hardware_reads_chip_and_memory_on_apple_silicon(ap, monkeypatch):
    monkeypatch.setattr(ap.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(ap.platform, "machine", lambda: "arm64")
    values = {"hw.memsize": str(24 * GIB), "machdep.cpu.brand_string": "Apple M4 Pro"}
    monkeypatch.setattr(ap, "_sysctl", lambda key: values[key])

    assert ap.detect_hardware() == {"chip": "Apple M4 Pro", "memory_bytes": 24 * GIB}


@pytest.mark.parametrize("name", ["apple-m4-16gb", "apple-m4pro-24gb"])
def test_shipped_profiles_only_override_keys_that_exist_in_example_config(ap, name):
    example = json.loads((ROOT / "config" / "config-example.json").read_text(encoding="utf-8"))
    overlay = ap.load_profile(ROOT / "config", name)

    def check(sub_overlay, sub_example, path=""):
        for key, value in sub_overlay.items():
            assert key in sub_example, f"{name}: unknown config key {path}{key}"
            if isinstance(value, dict):
                check(value, sub_example[key], f"{path}{key}.")

    check(overlay, example)


def test_24gb_profile_keeps_the_stock_defaults(ap):
    # Benchmarked on an M4 Pro: the stock defaults peak at ~6.5 GB, so nothing needs tuning.
    assert ap.load_profile(ROOT / "config", "apple-m4pro-24gb") == {}


def test_16gb_profile_only_unloads_models_after_translation(ap):
    # Size, batch and MPS-cap reductions did not lower peak memory in benchmarks (they only
    # slowed runs down), so the only difference is freeing models once translation is done.
    assert ap.load_profile(ROOT / "config", "apple-m4-16gb") == {"app": {"unload_models_after_translation": True}}


def test_applied_16gb_profile_keeps_every_other_default(ap, tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    shutil.copy(ROOT / "config" / "config-example.json", config_dir / "config-example.json")
    shutil.copytree(ROOT / "config" / "profiles", config_dir / "profiles")

    assert ap.apply_profile(config_dir, "apple-m4-16gb") == ap.APPLIED

    example = json.loads((config_dir / "config-example.json").read_text(encoding="utf-8"))
    result = json.loads((config_dir / "config.json").read_text(encoding="utf-8"))
    assert result["app"]["unload_models_after_translation"] is True
    example["app"]["unload_models_after_translation"] = True
    assert result == example


def _load_launch():
    spec = importlib.util.spec_from_file_location("launch_apple_profile_hook_test", ROOT / "packaging" / "launch.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_launcher_hook_never_fails_the_install(monkeypatch, capsys):
    import sys
    import types

    launch = _load_launch()
    broken = types.ModuleType("apple_profile")

    def boom():
        raise RuntimeError("sysctl exploded")

    broken.apply_for_this_machine = boom
    monkeypatch.setitem(sys.modules, "apple_profile", broken)

    launch.apply_apple_silicon_profile()  # must not raise

    assert "sysctl exploded" in capsys.readouterr().out


def test_launcher_hook_is_silent_off_apple_silicon(monkeypatch, capsys):
    import sys
    import types

    launch = _load_launch()
    stub = types.ModuleType("apple_profile")
    stub.apply_for_this_machine = lambda: None
    monkeypatch.setitem(sys.modules, "apple_profile", stub)

    launch.apply_apple_silicon_profile()

    assert capsys.readouterr().out == ""
