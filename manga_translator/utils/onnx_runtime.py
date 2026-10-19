from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

ModelPath = Union[str, Path]
_TRUE_VALUES = {"1", "true", "yes", "on"}
_DISABLE_ONNX_GPU = False
_ENABLE_ONNX_DIRECTML = False
_DML_PROVIDER = "DmlExecutionProvider"


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in _TRUE_VALUES


def set_onnx_gpu_disabled(disabled: bool) -> None:
    """Set process-wide ONNX GPU disable switch."""
    global _DISABLE_ONNX_GPU
    _DISABLE_ONNX_GPU = bool(disabled)


def is_onnx_gpu_disabled() -> bool:
    """Return True when ONNX GPU acceleration is disabled by config or env."""
    return _DISABLE_ONNX_GPU or _is_truthy(os.getenv("MT_DISABLE_ONNX_GPU", ""))


def set_onnx_directml_enabled(enabled: bool) -> None:
    """Set process-wide switch that lets ONNX sessions use DirectML (AMD/Intel GPUs on Windows)."""
    global _ENABLE_ONNX_DIRECTML
    _ENABLE_ONNX_DIRECTML = bool(enabled)


def _is_directml_requested() -> bool:
    # A non-empty MT_ONNX_DIRECTML overrides the config switch in both directions.
    env_value = os.getenv("MT_ONNX_DIRECTML", "").strip()
    if env_value:
        return _is_truthy(env_value)
    return _ENABLE_ONNX_DIRECTML


def is_onnx_directml_enabled() -> bool:
    """Return True when DirectML is requested by config or env and GPU use is not disabled."""
    return _is_directml_requested() and not is_onnx_gpu_disabled()


def import_onnxruntime(import_error_message: str = ""):
    """Import onnxruntime with a caller-provided error message."""
    try:
        import onnxruntime as ort  # type: ignore
    except Exception as exc:
        if import_error_message:
            raise ImportError(import_error_message) from exc
        raise
    return ort


def create_session_options(
    ort: Any,
    *,
    log_severity_level: int = 3,
    enable_mem_pattern: Optional[bool] = None,
    enable_cpu_mem_arena: Optional[bool] = None,
    intra_op_num_threads: Optional[int] = None,
    inter_op_num_threads: Optional[int] = None,
) -> Any:
    """Create SessionOptions using ONNX Runtime official defaults plus overrides."""
    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.log_severity_level = log_severity_level

    if enable_mem_pattern is not None:
        sess_options.enable_mem_pattern = bool(enable_mem_pattern)
    if enable_cpu_mem_arena is not None:
        sess_options.enable_cpu_mem_arena = bool(enable_cpu_mem_arena)
    if intra_op_num_threads is not None:
        sess_options.intra_op_num_threads = int(intra_op_num_threads)
    if inter_op_num_threads is not None:
        sess_options.inter_op_num_threads = int(inter_op_num_threads)

    return sess_options


def _provider_name(provider: Any) -> Optional[str]:
    if isinstance(provider, str):
        return provider
    if isinstance(provider, (tuple, list)) and provider:
        return provider[0]
    return None


def _provider_has_cuda(provider: Any) -> bool:
    return _provider_name(provider) == "CUDAExecutionProvider"


def _provider_has_gpu(provider: Any) -> bool:
    return _provider_name(provider) in ("CUDAExecutionProvider", _DML_PROVIDER)


def build_execution_providers(
    ort: Any,
    *,
    device: str = "cpu",
    cuda_options: Optional[Mapping[str, Any]] = None,
    disable_onnx_gpu: Optional[bool] = None,
    include_cpu: bool = True,
    preload_cuda_dlls: bool = True,
    logger: Any = None,
) -> list[Any]:
    """
    Build providers in ONNX Runtime official format:
    [("CUDAExecutionProvider", {...}), "CPUExecutionProvider"].

    When no CUDA provider is used and DirectML is enabled (``set_onnx_directml_enabled``
    or ``MT_ONNX_DIRECTML=1``), DmlExecutionProvider is placed before the CPU provider
    if the installed onnxruntime build exposes it.
    """
    normalized = (device or "cpu").lower()
    wants_cuda = normalized.startswith("cuda")
    onnx_gpu_disabled = is_onnx_gpu_disabled()
    if disable_onnx_gpu is not None:
        onnx_gpu_disabled = bool(disable_onnx_gpu) or onnx_gpu_disabled
    use_directml = not onnx_gpu_disabled and _is_directml_requested()
    providers: list[Any] = []

    if wants_cuda and onnx_gpu_disabled:
        if logger is not None:
            logger.info("ONNX GPU acceleration disabled by switch; forcing CPUExecutionProvider.")
        wants_cuda = False

    if wants_cuda:
        if preload_cuda_dlls and hasattr(ort, "preload_dlls"):
            try:
                ort.preload_dlls()
            except Exception as exc:
                if logger is not None:
                    logger.warning(f"onnxruntime.preload_dlls() failed: {exc}")

        available_providers: Sequence[str] = []
        try:
            available_providers = ort.get_available_providers()
        except Exception as exc:
            if logger is not None:
                logger.warning(f"Failed to query ONNX Runtime providers: {exc}")

        if "CUDAExecutionProvider" in available_providers:
            # ORT 1.28 on Windows can emit a misleading
            # "No registered plugin EP device" warning when device_id=0 is
            # passed explicitly.  CUDA selects device 0 by default; keep
            # provider options empty unless a caller explicitly overrides it.
            options = dict(cuda_options) if cuda_options else {}
            providers.append(("CUDAExecutionProvider", options))
        elif logger is not None and not use_directml:
            logger.warning(f"CUDAExecutionProvider not available, fallback to CPU: {available_providers}")

    if not providers and use_directml:
        available_providers = []
        try:
            available_providers = ort.get_available_providers()
        except Exception as exc:
            if logger is not None:
                logger.warning(f"Failed to query ONNX Runtime providers: {exc}")

        if _DML_PROVIDER in available_providers:
            providers.append(_DML_PROVIDER)
        elif logger is not None:
            logger.warning(
                f"{_DML_PROVIDER} not available, fallback to CPU "
                f"(install onnxruntime-directml): {available_providers}"
            )

    if include_cpu or not providers:
        providers.append("CPUExecutionProvider")

    return providers


class _CpuFallbackSession:
    """Wrap a DirectML session and move the model to CPU if inference fails on the GPU.

    DirectML errors (out of VRAM, device removed/TDR on older drivers) surface only at
    run() time, after session creation succeeded, so they need a runtime fallback.
    """

    def __init__(self, session: Any, create_cpu_session: Any, logger: Any = None):
        self._session = session
        self._create_cpu_session = create_cpu_session
        self._logger = logger
        self._on_cpu = False

    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self._on_cpu:
            return self._session.run(*args, **kwargs)
        try:
            return self._session.run(*args, **kwargs)
        except Exception as exc:
            # Bad inputs fail the same way on CPU; only device failures are worth a retry.
            if type(exc).__name__ == "InvalidArgument":
                raise
            if self._logger is not None:
                self._logger.warning(f"DirectML inference failed, switching this model to CPU: {exc}")
            self._session = self._create_cpu_session()
            self._on_cpu = True
            return self._session.run(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


def create_inference_session(
    ort: Any,
    model_path: ModelPath,
    *,
    device: str = "cpu",
    sess_options: Any,
    cuda_options: Optional[Mapping[str, Any]] = None,
    disable_onnx_gpu: Optional[bool] = None,
    logger: Any = None,
    fallback_to_cpu: bool = True,
    preload_cuda_dlls: bool = True,
) -> tuple[Any, str]:
    """
    Create InferenceSession with standard provider order and optional GPU->CPU fallback.
    Returns (session, active_device), where active_device is 'cuda', 'directml' or 'cpu'.
    DirectML sessions also fall back to CPU at run() time when fallback_to_cpu is set.
    """
    providers = build_execution_providers(
        ort,
        device=device,
        cuda_options=cuda_options,
        disable_onnx_gpu=disable_onnx_gpu,
        include_cpu=True,
        preload_cuda_dlls=preload_cuda_dlls,
        logger=logger,
    )

    model_path_str = str(model_path)
    tried_gpu = any(_provider_has_gpu(provider) for provider in providers)

    def create_cpu_session() -> Any:
        return ort.InferenceSession(
            model_path_str,
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

    if any(_provider_name(provider) == _DML_PROVIDER for provider in providers):
        # DirectML requires these two settings (ONNX Runtime DirectML EP docs).
        sess_options.enable_mem_pattern = False
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    try:
        session = ort.InferenceSession(model_path_str, sess_options=sess_options, providers=providers)
    except Exception as exc:
        if fallback_to_cpu and tried_gpu:
            if logger is not None:
                logger.warning(f"GPU session creation failed, fallback to CPU: {exc}")
            session = create_cpu_session()
        else:
            raise

    active_providers = session.get_providers()
    if "CUDAExecutionProvider" in active_providers:
        active_device = "cuda"
    elif _DML_PROVIDER in active_providers:
        active_device = "directml"
        if logger is not None:
            logger.info(f"ONNX Runtime is using DirectML for {Path(model_path_str).name}")
        if fallback_to_cpu:
            session = _CpuFallbackSession(session, create_cpu_session, logger)
    else:
        active_device = "cpu"
    return session, active_device
