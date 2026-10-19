# Hardware profile: NVIDIA RTX 2060 Super (8 GB)

This branch (`rtx-2060-super`) keeps the default settings, which suit an 8 GB Turing card:
every stage runs on CUDA, inpainting uses `lama_large` at 2048 px, and a stage that runs out
of VRAM is retried on the CPU (`oom_fallback_to_cpu`). Other profiles: `rx-580-2048sp`
(AMD RX 580, Windows 10) and `apple-m4` (Mac M4 / M4 Pro).

## Dependencies

Turing (compute capability 7.5) supports CUDA 13, so the `cuda13.0` group applies:

```bat
uv sync --locked --no-default-groups --group cuda13.0
```

`inpainting_precision` stays `fp32`: LaMa switches `fp16` to `bf16`, which Turing cannot run, so
PyTorch would disable autocast and fall back to fp32 anyway.

## Sharing the settings

`config/rtx2060super-preset.json` holds only this profile's hardware settings. Load it with
**Settings → Import Config**: it changes only those settings and keeps the other person's
translator, language and API keys.

## Updating

**Do not use the in-app updater or `Win-Install-or-Update.bat` on this branch.** They only
follow the upstream `main`/`beta` branches: the update switches the checkout to `main`, and the
install option also points `origin` at the upstream repository. Automatic update checks are off
in this profile (`app.auto_check_updates` = `false`). To update, run `git pull` and then the
`uv sync` command above.
