#!/usr/bin/env bash
# ============================================================
#  Manga Translator UI - launcher for Apple Silicon Macs (M4 / M4 Pro)
#  Run Mac-M4-Install.command first.
#  Do not use the in-app updater on this branch: it switches the code to "main".
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Run PyTorch operations that Metal (MPS) does not implement on the CPU instead of failing.
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"

if [ ! -x ".venv/bin/python" ]; then
    printf '[ERROR] Environment not found. Run Mac-M4-Install.command first.\n' >&2
    exit 1
fi

echo "Starting..."
echo "========================================"
exec ".venv/bin/python" desktop_qt_ui/main.py "$@"
