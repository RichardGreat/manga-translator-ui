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
| `cli.disable_onnx_gpu` | `false` | `true` | ONNX Runtime runs on CPU only |
| `cli.batch_size` | 3 | 1 | keep peak RAM low |
| `detector.detection_size` | 2048 | 1536 | faster CPU detection |
| `inpainter.inpainter` | `lama_large` | `lama_mpe` | much lighter on CPU |
| `inpainter.inpainting_size` | 2048 | 1024 | faster, less RAM |
| `upscale.tile_size` | 400 | 200 | smaller tiles, lower RAM |
| `colorizer.colorization_size` | 2048 | 1024 | faster, less RAM |

The per-stage `device_*` options stay on `auto`, so they follow `use_gpu` (CPU here).
If you later get a working GPU backend, set `use_gpu` to `true` and pick `gpu` for the
stages you want accelerated; `oom_fallback_to_cpu` will retry on CPU if 4 GB runs out.
