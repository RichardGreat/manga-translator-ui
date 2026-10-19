# Hardware profile: Windows 10 / Intel i5-10400 / 16 GB RAM / AMD RX 580 2048SP (4 GB)

This branch (`rx-580-2048sp`) ships `config/config-example.json` pre-tuned for this PC
and two scripts for Windows 10. The RTX 2060 Super profile lives on the `rtx-2060-super` branch.

## Quick start

1. Put the project in a short path with English letters only, e.g. `C:\manga-translator-ui`.
2. Double-click **`Win10-RX580-Install.bat`**. It installs everything and, at the end, offers to
   start the app (pass `--no-start` to skip that).
3. Later, start the app with **`Win10-RX580-Start.bat`**.

## How the hardware is used

The RX 580 is a Polaris card (gfx803). PyTorch has no backend for it: the project's ROCm
builds do not support Polaris and CUDA is NVIDIA-only. So:

- **PyTorch stages** (detection, 48px OCR, PyTorch inpainting/upscaling) run on the
  6-core i5-10400 (`cli.use_gpu` = `false`).
- **ONNX stages** (`lama_mpe` / `lama` inpainting, PaddleOCR, booru tagger) run on the
  RX 580 through **DirectML** (`onnxruntime-directml`, `cli.onnx_directml` = `true`).
  The default inpainter of this profile, `lama_mpe`, uses ONNX, so inpainting, the
  heaviest stage, runs on the GPU.

When a model really runs on the GPU the log shows
`ONNX Runtime is using DirectML for <model>.onnx`. If DirectML is unavailable, the session
cannot be created, or inference fails on the GPU (out of the 4 GB VRAM, driver reset), a
warning is logged and that model continues on the CPU, so a translation does not fail
because of the GPU.

## What `Win10-RX580-Install.bat` does

1. Checks for 64-bit Windows 10 version 1903 (build 18362) or newer, which DirectML needs, and
   warns about project paths with non-English characters or paths too long for Windows 10.
2. Installs the Microsoft Visual C++ runtime if it is missing (PyTorch needs it; accept the
   administrator prompt).
3. Installs [`uv`](https://docs.astral.sh/uv/) if it is missing.
4. Installs Python 3.12 through uv and runs
   `uv sync --locked --no-default-groups --group directml` into `.venv`
   (CPU PyTorch + `onnxruntime-directml`; about 1-2 GB on the first run).
5. Prints the GPU and driver version and checks that PyTorch and DirectML load.

Run it again at any time to repair the environment. `onnxruntime-directml` and `onnxruntime`
share a package name, so never install both into the same environment.

## Updating

**Do not use the in-app updater or `Win-Install-or-Update.bat` on this branch.** The updater
only follows the `main` and `beta` branches and would switch the code to `main`, dropping this
profile. Automatic update checks are therefore off in this profile (`app.auto_check_updates` =
`false`). To update:

```bat
git pull
Win10-RX580-Install.bat
```

## Settings changed versus the default config

| Setting | Default | This profile | Reason |
|---|---|---|---|
| `app.auto_check_updates` | `true` | `false` | the updater would switch to `main` |
| `cli.use_gpu` | `true` | `false` | no PyTorch backend for the RX 580 |
| `cli.onnx_directml` | `false` | `true` | run ONNX models on the RX 580 through DirectML |
| `cli.batch_size` | 3 | 1 | keep peak RAM low |
| `detector.detection_size` | 2048 | 1536 | faster CPU detection |
| `inpainter.inpainter` | `lama_large` | `lama_mpe` | ONNX model: runs on DirectML, light on CPU |
| `inpainter.inpainting_size` | 2048 | 1024 | faster, fits in 4 GB VRAM |
| `upscale.tile_size` | 400 | 200 | smaller tiles, lower RAM |
| `colorizer.colorization_size` | 2048 | 1024 | faster, less RAM |

## Sharing the settings

`config/rx580-2048sp-preset.json` holds only the settings of this profile (the table above,
without `app.auto_check_updates`). Send that file and load it with **Settings → Import Config**:
it changes only those settings and keeps the other person's translator, language and API keys.
DirectML (`cli.onnx_directml`) needs this branch's code and `Win10-RX580-Install.bat`; on a stock
install that key is ignored and the rest still applies. The full defaults are in
`config/config-example.json`; your own saved settings are in `config/config.json` (not in git).

## Turning DirectML off

- For one run: `set MT_ONNX_DIRECTML=0` in a console, then run `Win10-RX580-Start.bat`
  from the same console. A non-empty `MT_ONNX_DIRECTML` overrides `cli.onnx_directml`.
- Permanently: set `cli.disable_onnx_gpu` to `true` in `config/config.json`.

Keep the AMD Radeon driver up to date; DirectML needs a DirectX 12 capable driver.
The per-stage `device_*` options stay on `auto`, so they follow `use_gpu` (CPU here).
