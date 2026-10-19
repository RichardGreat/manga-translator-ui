# Hardware profile: Intel i5-10400 / 16 GB RAM / AMD RX 580 2048SP (4 GB)

This branch (`rx-580-2048sp`) ships `config/config-example.json` pre-tuned for this PC.
The RTX 2060 Super profile lives on the `rtx-2060-super` branch.

## Why the GPU is not used by PyTorch

The RX 580 is a Polaris card (gfx803). The ROCm PyTorch builds used by this project
(`rocm7.2.1` dependency group) do not support it, and CUDA is NVIDIA-only. The installer
therefore falls back to the **CPU** build; choose option `[1] CPU` when it asks about an
unsupported AMD GPU. The 6-core i5-10400 and 16 GB RAM do the work.

## What changed versus the default config

| Setting | Default | This profile | Reason |
|---|---|---|---|
| `cli.use_gpu` | `true` | `false` | no supported GPU backend |
| `cli.onnx_directml` | `false` | `true` | run ONNX models on the RX 580 through DirectML |
| `cli.batch_size` | 3 | 1 | keep peak RAM low |
| `detector.detection_size` | 2048 | 1536 | faster CPU detection |
| `inpainter.inpainter` | `lama_large` | `lama_mpe` | much lighter on CPU |
| `inpainter.inpainting_size` | 2048 | 1024 | faster, less RAM |
| `upscale.tile_size` | 400 | 200 | smaller tiles, lower RAM |
| `colorizer.colorization_size` | 2048 | 1024 | faster, less RAM |

## GPU acceleration through DirectML (Windows)

PyTorch cannot use the RX 580, but ONNX Runtime can, via DirectML. The ONNX models
(`lama_mpe`/`lama` inpainting, PaddleOCR, booru tagger) then run on the GPU while
PyTorch stages (detection, 48px OCR, etc.) stay on the CPU.

1. Double-click **`Win10-RX580-Install.bat`** (Windows 10 version 1903 / build 18362 or newer).
   It installs the Visual C++ runtime if missing, installs `uv`, creates `.venv` with
   Python 3.12 and runs `uv sync --locked --no-default-groups --group directml`
   (CPU PyTorch + `onnxruntime-directml`), then checks that `DmlExecutionProvider` is
   visible. Run it again at any time to repair or update. `onnxruntime-directml` and
   `onnxruntime` share a package name, so do not install both.
2. Start the app with **`Win10-RX580-Start.bat`**. It sets `MT_ONNX_DIRECTML=1`; the same is
   already the default via `cli.onnx_directml` = `true` in `config/config-example.json`.
3. If `onnxruntime-directml` is not installed or the GPU session fails (e.g. out of the
   4 GB VRAM), a warning is logged and that model falls back to the CPU.
4. Keep the Radeon driver up to date; DirectML needs a DirectX 12 capable driver.
5. `cli.disable_onnx_gpu` = `true` turns DirectML off again.

The per-stage `device_*` options stay on `auto`, so they follow `use_gpu` (CPU here).
If you later get a working GPU backend, set `use_gpu` to `true` and pick `gpu` for the
stages you want accelerated; `oom_fallback_to_cpu` will retry on CPU if 4 GB runs out.
