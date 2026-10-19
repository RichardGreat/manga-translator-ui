import _bootstrap  # noqa: F401

from manga_translator.utils.onnx_runtime import build_execution_providers


def test_cuda_provider_does_not_pass_default_device_id():
    class FakeOrt:
        def __init__(self):
            self.preload_calls = 0

        def preload_dlls(self):
            self.preload_calls += 1

        @staticmethod
        def get_available_providers():
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    ort = FakeOrt()

    providers = build_execution_providers(ort, device="cuda")

    assert providers == [
        ("CUDAExecutionProvider", {}),
        "CPUExecutionProvider",
    ]
    assert ort.preload_calls == 1


def test_cuda_provider_keeps_explicit_options():
    class FakeOrt:
        @staticmethod
        def get_available_providers():
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    assert build_execution_providers(
        FakeOrt(),
        device="cuda",
        cuda_options={"arena_extend_strategy": "kSameAsRequested"},
    ) == [
        (
            "CUDAExecutionProvider",
            {"arena_extend_strategy": "kSameAsRequested"},
        ),
        "CPUExecutionProvider",
    ]


class _DmlOrt:
    ExecutionMode = type("ExecutionMode", (), {"ORT_SEQUENTIAL": "seq"})

    @staticmethod
    def get_available_providers():
        return ["DmlExecutionProvider", "CPUExecutionProvider"]


def test_directml_provider_used_when_enabled():
    from manga_translator.utils import onnx_runtime

    onnx_runtime.set_onnx_directml_enabled(True)
    try:
        assert build_execution_providers(_DmlOrt(), device="cpu") == [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]
        onnx_runtime.set_onnx_gpu_disabled(True)
        assert build_execution_providers(_DmlOrt(), device="cpu") == ["CPUExecutionProvider"]
    finally:
        onnx_runtime.set_onnx_gpu_disabled(False)
        onnx_runtime.set_onnx_directml_enabled(False)


def test_directml_not_used_by_default_or_when_unavailable():
    from manga_translator.utils import onnx_runtime

    assert build_execution_providers(_DmlOrt(), device="cpu") == ["CPUExecutionProvider"]

    class CpuOnlyOrt:
        @staticmethod
        def get_available_providers():
            return ["CPUExecutionProvider"]

    onnx_runtime.set_onnx_directml_enabled(True)
    try:
        assert build_execution_providers(CpuOnlyOrt(), device="cpu") == ["CPUExecutionProvider"]
    finally:
        onnx_runtime.set_onnx_directml_enabled(False)


def test_directml_session_sets_required_options_and_reports_device():
    from manga_translator.utils import onnx_runtime

    class Opts:
        enable_mem_pattern = True
        execution_mode = None

    class Session:
        def __init__(self, path, sess_options, providers):
            self.providers = providers

        def get_providers(self):
            return self.providers

    class Ort(_DmlOrt):
        InferenceSession = Session

    opts = Opts()
    onnx_runtime.set_onnx_directml_enabled(True)
    try:
        session, device = onnx_runtime.create_inference_session(Ort, "m.onnx", sess_options=opts)
    finally:
        onnx_runtime.set_onnx_directml_enabled(False)

    assert device == "directml"
    assert opts.enable_mem_pattern is False
    assert opts.execution_mode == "seq"
