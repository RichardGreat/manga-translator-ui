#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple Silicon performance profiles.

Apple Silicon shares one memory pool between the CPU and the GPU (MPS), so the
dedicated-VRAM defaults in config/config-example.json are too heavy for a 16 GB
machine. A profile is a sparse JSON overlay in config/profiles/ that is merged
onto config-example.json to produce config/config.json.

Profiles are applied automatically after a macOS install, and only when the
user has no config/config.json yet. An existing config is never touched
unless --force is given (a config.json.bak copy is kept in that case).

    python packaging/apple_profile.py --show
    python packaging/apple_profile.py --apply [--profile NAME] [--force]

This module only uses the standard library: it runs before the heavy
dependencies are installed.
"""

from __future__ import annotations

import argparse
import copy
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

PROFILE_16GB = "apple-m4-16gb"
PROFILE_24GB = "apple-m4pro-24gb"

# hw.memsize reports 17179869184 (16 GiB) on a 16 GB Mac and 25769803776 on a
# 24 GB one. Anything below this threshold (8 GB included) gets the
# conservative profile; 24 GB and up (M4 Max etc.) get the larger one.
MEMORY_THRESHOLD_BYTES = 20 * 1024**3

APPLIED = "applied"
SKIPPED_EXISTING = "skipped-existing"

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def _sysctl(key: str) -> str:
    return subprocess.check_output(["sysctl", "-n", key], text=True, timeout=5).strip()


def detect_hardware() -> Optional[dict[str, Any]]:
    """Return {"chip", "memory_bytes"} on Apple Silicon, otherwise None."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return None
    try:
        memory_bytes = int(_sysctl("hw.memsize"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    try:
        chip = _sysctl("machdep.cpu.brand_string")
    except (OSError, subprocess.SubprocessError):
        chip = "Apple Silicon"
    return {"chip": chip, "memory_bytes": memory_bytes}


def select_profile(memory_bytes: int) -> str:
    return PROFILE_24GB if memory_bytes >= MEMORY_THRESHOLD_BYTES else PROFILE_16GB


def deep_merge(base: dict, overlay: dict) -> dict:
    """Return base with overlay applied recursively; neither input is mutated."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_profile(config_dir: Path, name: str) -> dict:
    path = Path(config_dir) / "profiles" / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown Apple Silicon profile: {name} ({path})")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_profile(config_dir: Path, name: str, force: bool = False) -> str:
    """Write config/config.json = config-example.json + profile overlay."""
    config_dir = Path(config_dir)
    overlay = load_profile(config_dir, name)
    target = config_dir / "config.json"

    if target.exists() and not force:
        return SKIPPED_EXISTING

    with open(config_dir / "config-example.json", "r", encoding="utf-8") as f:
        example = json.load(f)

    if target.exists():
        shutil.copy2(target, config_dir / "config.json.bak")

    with open(target, "w", encoding="utf-8") as f:
        json.dump(deep_merge(example, overlay), f, ensure_ascii=False, indent=2)
        f.write("\n")
    return APPLIED


def apply_for_this_machine(config_dir: Path = CONFIG_DIR, force: bool = False) -> Optional[tuple[str, str]]:
    """Detect, pick and apply. Returns (profile, status), or None off Apple Silicon."""
    hardware = detect_hardware()
    if hardware is None:
        return None
    name = select_profile(hardware["memory_bytes"])
    return name, apply_profile(config_dir, name, force=force)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Apple Silicon performance profiles")
    parser.add_argument("--show", action="store_true", help="print the detected hardware and chosen profile")
    parser.add_argument("--apply", action="store_true", help="write config/config.json from the profile")
    parser.add_argument("--profile", help=f"override auto-detection ({PROFILE_16GB} or {PROFILE_24GB})")
    parser.add_argument("--force", action="store_true", help="overwrite an existing config.json (backup kept)")
    args = parser.parse_args(argv)

    hardware = detect_hardware()
    if hardware is None and not args.profile:
        print("Not an Apple Silicon Mac; no profile applies.")
        return 0

    name = args.profile or select_profile(hardware["memory_bytes"])
    if hardware is not None:
        print(f"Detected: {hardware['chip']}, {hardware['memory_bytes'] / 1024**3:.0f} GB")
    print(f"Profile:  {name}")

    if args.apply:
        status = apply_profile(CONFIG_DIR, name, force=args.force)
        if status == SKIPPED_EXISTING:
            print("config/config.json already exists; left unchanged (use --force to replace it).")
        else:
            print("Wrote config/config.json")
    elif not args.show:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
