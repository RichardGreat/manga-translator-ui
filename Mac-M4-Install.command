#!/usr/bin/env bash
# ============================================================
#  Manga Translator UI - installer for Apple Silicon Macs
#    MacBook / Mac mini with M4 (16 GB) or M4 Pro (24 GB)
#
#  What it does:
#    1. checks the Mac (Apple Silicon, macOS 14 Sonoma or newer for PyTorch 2.13)
#    2. installs uv (Python package manager) if it is missing
#    3. installs Python 3.12 and the "metal" dependency group into .venv
#       (PyTorch with the Apple GPU backend, MPS)
#    4. checks that PyTorch can use the GPU
#    5. on the first install, creates config/config.json from the preset that
#       matches this Mac's memory (16 GB or 24 GB+)
#    6. offers to start the app
#
#  Double-click it in Finder, or run:  bash Mac-M4-Install.command
#  Run it again at any time to repair the environment or after "git pull".
#  Do NOT use Unix-Install-or-Update.sh or the in-app updater on this branch:
#  they switch the code to the upstream "main" branch.
#
#  Options:  --no-start   do not offer to start the app at the end
# ============================================================

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
ENV_PY="$SCRIPT_DIR/.venv/bin/python"
UV=""
NO_START=0
for arg in "$@"; do
    case "$arg" in
        --no-start) NO_START=1 ;;
    esac
done

info() { printf '[*] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; }

on_error() {
    local status=$?
    fail "Installation stopped (line ${BASH_LINENO[0]:-?}, exit code $status). Fix the message above and run this file again."
    exit "$status"
}
trap on_error ERR

echo "============================================================"
echo " Manga Translator UI - install for Apple M4 / M4 Pro (Metal)"
echo "============================================================"
echo

# ---------- 1) Mac ----------
info "[1/6] Checking the Mac..."
if [ "$(uname -s)" != "Darwin" ]; then
    fail "This installer is for macOS."
    exit 1
fi
if [ "$(sysctl -n sysctl.proc_translated 2>/dev/null || echo 0)" = "1" ]; then
    fail "Terminal is running under Rosetta (Intel mode)."
    fail "Turn off 'Open using Rosetta' for Terminal (Finder > Applications > Utilities > Terminal > Get Info) and try again."
    exit 1
fi
if [ "$(uname -m)" != "arm64" ]; then
    fail "An Apple Silicon Mac (M1 or newer) is required; this Mac reports $(uname -m)."
    exit 1
fi

MACOS_VERSION="$(sw_vers -productVersion)"
MACOS_MAJOR="${MACOS_VERSION%%.*}"
if [ "$MACOS_MAJOR" -lt 14 ]; then
    fail "macOS 14 Sonoma or newer is required (PyTorch 2.13); this Mac runs macOS $MACOS_VERSION."
    exit 1
fi

CHIP="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon')"
MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
if [ "$MEM_GB" -ge 24 ]; then
    PRESET="config/m4-pro-24gb-preset.json"
    PROFILE="24 GB+ (M4 Pro profile)"
else
    PRESET="config/m4-16gb-preset.json"
    PROFILE="16 GB (M4 profile)"
    if [ "$MEM_GB" -lt 16 ]; then
        warn "Only ${MEM_GB} GB of memory: large pages may be slow. Close other apps while translating."
    fi
fi
ok "$CHIP, ${MEM_GB} GB memory, macOS $MACOS_VERSION -> $PROFILE"

# ---------- 2) uv ----------
info "[2/6] Checking uv..."
find_uv() {
    local candidate
    candidate="$(command -v uv 2>/dev/null || true)"
    if [ -n "$candidate" ]; then
        UV="$candidate"
        return 0
    fi
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
        if [ -x "$candidate" ]; then
            UV="$candidate"
            return 0
        fi
    done
    return 1
}
if ! find_uv; then
    info "uv not found; installing it with the official installer (https://astral.sh/uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if ! find_uv; then
        fail "uv installation failed. See https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi
ok "Using $UV"

# ---------- 3) Python 3.12 + dependencies ----------
info "[3/6] Installing Python 3.12 and dependencies (first run downloads about 1 GB)..."
"$UV" python install 3.12
"$UV" sync --locked --no-default-groups --group metal

# ---------- 4) Verify ----------
info "[4/6] Checking PyTorch and the GPU (Metal / MPS)..."
set +e
"$ENV_PY" -c "
import sys, torch
print('    torch', torch.__version__)
if not torch.backends.mps.is_available():
    sys.exit(3)
x = torch.ones(4, device='mps')
print('    MPS works:', float((x * 2).sum()) == 8.0)
"
RC=$?
set -e
if [ "$RC" = "3" ]; then
    warn "PyTorch cannot use the GPU (MPS). The app will run on the CPU; update macOS and run this file again."
elif [ "$RC" != "0" ]; then
    fail "PyTorch failed to load (code $RC). Run this file again; if it persists, delete the .venv folder and retry."
    exit 1
fi

# ---------- 5) Settings ----------
info "[5/6] Settings..."
if [ -f "config/config.json" ]; then
    ok "Keeping your existing config/config.json."
    echo "    To apply the $PROFILE settings: Settings > Import Config > $PRESET"
else
    "$ENV_PY" - "$PRESET" <<'PY'
import json, sys

with open("config/config-example.json", encoding="utf-8") as f:
    config = json.load(f)
with open(sys.argv[1], encoding="utf-8") as f:
    preset = json.load(f)
for section, values in preset.items():
    config.setdefault(section, {}).update(values)
with open("config/config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
    ok "Created config/config.json from $PRESET"
fi

# Let Finder open the start script without the "downloaded from the internet" prompt.
xattr -d com.apple.quarantine "$SCRIPT_DIR/Mac-M4-Start.command" 2>/dev/null || true

# ---------- 6) Done ----------
echo
echo "============================================================"
echo " [6/6] Done. Start the app with Mac-M4-Start.command"
echo "============================================================"
if [ "$NO_START" = "0" ] && [ -t 0 ]; then
    read -r -p "Start the app now? [Y/n] " ANSWER || ANSWER="n"
    case "${ANSWER:-Y}" in
        [Yy]*) exec bash "$SCRIPT_DIR/Mac-M4-Start.command" ;;
    esac
fi
