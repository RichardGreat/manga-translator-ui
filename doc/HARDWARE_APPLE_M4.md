# Hardware profile: Apple M4 (16 GB) and M4 Pro (24 GB)

This branch (`apple-m4`) supports both Macs. `config/config-example.json` is tuned for the
16 GB M4; the installer picks the M4 Pro settings automatically on Macs with 24 GB or more.
Other profiles: `rtx-2060-super` (NVIDIA) and `rx-580-2048sp` (AMD RX 580, Windows 10).

## Quick start

1. Get this branch: `git clone -b apple-m4 https://github.com/RichardGreat/manga-translator-ui.git`
   (or download it as a ZIP from GitHub).
2. Double-click **`Mac-M4-Install.command`** in Finder. If macOS says it cannot be opened, right-click
   it and choose **Open**, or run `bash Mac-M4-Install.command` in Terminal.
   At the end it offers to start the app (pass `--no-start` to skip that).
3. Later, start the app with **`Mac-M4-Start.command`**.

Requirements: Apple Silicon, macOS 14 Sonoma or newer (PyTorch 2.13 needs it; M4 Macs ship with
macOS 15), and several GB of free disk space for the environment and the models it downloads.

## What `Mac-M4-Install.command` does

1. Checks for Apple Silicon (and that Terminal is not running under Rosetta) and macOS 14+.
2. Installs [`uv`](https://docs.astral.sh/uv/) if it is missing.
3. Installs Python 3.12 through uv and runs
   `uv sync --locked --no-default-groups --group metal` into `.venv`
   (PyTorch with the Apple GPU backend, MPS). No Xcode is needed.
4. Checks that PyTorch can run a small computation on the GPU.
5. On the first install only, creates `config/config.json` from the preset that matches the
   Mac's memory. An existing `config/config.json` is never changed.

## How the hardware is used

- `cli.use_gpu` = `true` puts every PyTorch stage (detection, OCR, `lama_large` inpainting,
  upscaling) on the GPU through Metal (MPS). ONNX models such as PaddleOCR run on the CPU.
- The GPU shares the Mac's memory. If a stage runs out of it, the stage is retried on the CPU
  (`oom_fallback_to_cpu`) and the GPU memory cache is released.
- `Mac-M4-Start.command` sets `PYTORCH_ENABLE_MPS_FALLBACK=1`, so an operation that Metal does not
  implement runs on the CPU instead of stopping the translation.

## Settings per Mac

| Setting | M4, 16 GB (`m4-16gb-preset.json`, default) | M4 Pro, 24 GB (`m4-pro-24gb-preset.json`) |
|---|---|---|
| `cli.use_gpu` | `true` | `true` |
| `cli.batch_size` | 2 | 3 |
| `detector.detection_size` | 2048 | 2048 |
| `inpainter.inpainter` | `lama_large` | `lama_large` |
| `inpainter.inpainting_size` | 1536 | 2048 |
| `inpainter.inpainting_precision` | `fp32` (MPS runs LaMa in fp32) | `fp32` |
| `upscale.tile_size` | 256 | 400 |
| `colorizer.colorization_size` | 1536 | 2048 |

Both presets also set every `device_*` option to `auto` and `oom_fallback_to_cpu` to `true`.
On the 16 GB M4, close memory-hungry apps (browsers, editors) while translating large batches.

## Sharing or switching the settings

Send `config/m4-16gb-preset.json` or `config/m4-pro-24gb-preset.json` and load it with
**Settings → Import Config**: it changes only these settings and keeps the translator, language and
API keys. Your own saved settings are in `config/config.json` (not in git).

## Updating

**Do not use the in-app updater or `Unix-Install-or-Update.sh` on this branch.** They only follow
the upstream `main`/`beta` branches and would switch the code to `main`. Automatic update checks are
off in this profile (`app.auto_check_updates` = `false`). To update:

```bash
git pull
bash Mac-M4-Install.command
```
