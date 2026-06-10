import io
import json
import subprocess
import sys
import time
import types
import wave
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import backend.app as app_module
from backend.schemas import CommandOutcome
from backend.voice.audio_utils import AudioValidationError, validate_wav_bytes
from backend.voice.stt_service import STTService
from backend.voice.tts_service import TTSService, TTSUnavailableError
from backend.voice.voice_pipeline import LocalVoicePipeline


def wav_bytes(*, seconds=0.1, sample_rate=16000, channels=1, sample_width=2):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00" * int(seconds * sample_rate * channels * sample_width))
    return output.getvalue()


def test_audio_validation_accepts_bounded_mono_pcm_wav():
    info = validate_wav_bytes(wav_bytes())
    assert info.channels == 1
    assert info.sample_rate == 16000


@pytest.mark.parametrize(
    "audio",
    [
        b"",
        b"not-a-wav",
        wav_bytes(channels=2),
        wav_bytes(sample_rate=8000),
        wav_bytes(sample_width=1),
    ],
)
def test_audio_validation_rejects_invalid_audio(audio):
    with pytest.raises(AudioValidationError):
        validate_wav_bytes(audio)


def test_audio_validation_rejects_configured_size_and_duration_limits(monkeypatch):
    monkeypatch.setattr("config.VOICE_MAX_UPLOAD_BYTES", 20)
    with pytest.raises(AudioValidationError, match="size limit"):
        validate_wav_bytes(wav_bytes())

    monkeypatch.setattr("config.VOICE_MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr("config.VOICE_MAX_DURATION_SECONDS", 0.01)
    with pytest.raises(AudioValidationError, match="duration limit"):
        validate_wav_bytes(wav_bytes(seconds=0.1))


class FakeSTT:
    provider = "fake"

    def __init__(self, transcript="what time is it"):
        self.transcript = transcript

    def status(self):
        return {"provider": "fake", "available": True}

    def transcribe(self, _audio):
        return self.transcript


class FakeTTS:
    provider = "fake"

    def status(self):
        return {"provider": "fake", "available": True}

    def synthesize(self, _text):
        return b"RIFFfake"


class UnavailableTTS(FakeTTS):
    def synthesize(self, _text):
        raise TTSUnavailableError("Fake provider is unavailable")


class TimeoutTTS(FakeTTS):
    def synthesize(self, _text):
        raise TTSUnavailableError("Fake provider timed out")


def test_voice_pipeline_uses_same_command_gateway():
    calls = []
    pipeline = LocalVoicePipeline(FakeSTT(), FakeTTS())

    result = pipeline.execute(
        wav_bytes(),
        lambda text, **kwargs: calls.append((text, kwargs)) or CommandOutcome("Done", "success"),
    )

    assert calls[0][0] == "what time is it"
    assert calls[0][1]["mode"] == "local_voice"
    assert isinstance(result.outcome, CommandOutcome)
    assert result.audio == b"RIFFfake"
    assert [step["stage"] for step in result.outcome.metadata["decision_trace"]] == ["stt", "tts"]


def test_voice_confirmation_requires_spoken_yes():
    pipeline = LocalVoicePipeline(FakeSTT("maybe"), FakeTTS())
    result = pipeline.execute(
        wav_bytes(),
        lambda *_args, **_kwargs: pytest.fail("command must not execute"),
        pending_command="close spotify",
    )
    assert result.outcome.action_status == "confirmation_required"
    assert result.audio == b"RIFFfake"
    assert [step["stage"] for step in result.outcome.metadata["decision_trace"]] == [
        "stt",
        "voice_confirmation",
        "tts",
    ]


def test_voice_confirmation_cancellation_is_synthesized():
    pipeline = LocalVoicePipeline(FakeSTT("no"), FakeTTS())
    result = pipeline.execute(
        wav_bytes(),
        lambda *_args, **_kwargs: pytest.fail("command must not execute"),
        pending_command="close spotify",
    )

    assert result.outcome.action_status == "cancelled"
    assert result.audio == b"RIFFfake"
    assert result.outcome.metadata["decision_trace"][1]["status"] == "cancelled"


def test_voice_confirmation_executes_only_after_spoken_yes():
    calls = []
    pipeline = LocalVoicePipeline(FakeSTT("yes"), FakeTTS())
    pipeline.execute(
        wav_bytes(),
        lambda text, **kwargs: calls.append((text, kwargs)) or CommandOutcome("Done", "success"),
        pending_command="close spotify",
    )
    assert calls[0][1]["confirm"] is True
    assert calls[0][1]["pending_command"] == "close spotify"


def test_voice_trace_wraps_orchestrator_trace_and_excludes_private_text():
    private_transcript = "private spoken command"
    private_response = "private response text"
    pipeline = LocalVoicePipeline(FakeSTT(private_transcript), FakeTTS())
    outcome = CommandOutcome(
        private_response,
        "success",
        metadata={"decision_trace": [{"stage": "safety", "status": "allowed"}]},
    )

    result = pipeline.execute(wav_bytes(), lambda *_args, **_kwargs: outcome)

    trace = result.outcome.metadata["decision_trace"]
    assert [step["stage"] for step in trace] == ["stt", "safety", "tts"]
    assert trace[0]["provider"] == "fake"
    assert private_transcript not in json.dumps(trace)
    assert private_response not in json.dumps(trace)


def test_voice_trace_marks_disabled_and_unavailable_tts():
    disabled = LocalVoicePipeline(FakeSTT(), FakeTTS()).execute(
        wav_bytes(),
        lambda *_args, **_kwargs: CommandOutcome("Done", "success"),
        synthesize=False,
    )
    unavailable = LocalVoicePipeline(FakeSTT(), UnavailableTTS()).execute(
        wav_bytes(),
        lambda *_args, **_kwargs: CommandOutcome("Done", "success"),
    )

    assert disabled.outcome.metadata["decision_trace"][-1]["status"] == "skipped"
    assert unavailable.outcome.metadata["decision_trace"][-1]["status"] == "unavailable"
    assert unavailable.audio is None

    timed_out = LocalVoicePipeline(FakeSTT(), TimeoutTTS()).execute(
        wav_bytes(),
        lambda *_args, **_kwargs: CommandOutcome("Done", "success"),
    )
    assert timed_out.outcome.metadata["decision_trace"][-1]["reason"] == "timeout"


def _make_vosk_model_dir(tmp_path):
    model_path = tmp_path / "vosk-model"
    for name in ("am", "conf", "graph"):
        (model_path / name).mkdir(parents=True)
    return model_path


def test_vosk_model_is_cached_but_recognizer_is_per_request(monkeypatch, tmp_path):
    loads = []
    recognizers = []

    class FakeModel:
        def __init__(self, path):
            loads.append(path)

    class FakeRecognizer:
        def __init__(self, model, sample_rate):
            recognizers.append((model, sample_rate))

        def AcceptWaveform(self, _chunk):
            return True

        def FinalResult(self):
            return '{"text": "hello"}'

    monkeypatch.setitem(
        sys.modules,
        "vosk",
        types.SimpleNamespace(Model=FakeModel, KaldiRecognizer=FakeRecognizer),
    )
    monkeypatch.setattr(
        "config.VOSK_MODEL_PATH",
        str(_make_vosk_model_dir(tmp_path)),
    )
    service = STTService("vosk")

    assert service.transcribe(wav_bytes()) == "hello"
    assert service.transcribe(wav_bytes()) == "hello"
    assert len(loads) == 1
    assert len(recognizers) == 2


def test_whisper_model_is_cached_across_transcriptions(monkeypatch, tmp_path):
    loads = []

    class Segment:
        text = " hello "

    class FakeWhisperModel:
        def __init__(self, path, **kwargs):
            loads.append((path, kwargs))

        def transcribe(self, _path, **_kwargs):
            return [Segment()], None

    model_path = tmp_path / "whisper-model"
    model_path.mkdir()
    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setattr("config.WHISPER_MODEL_PATH", str(model_path))
    service = STTService("faster-whisper")

    assert service.transcribe(wav_bytes()) == "hello"
    assert service.transcribe(wav_bytes()) == "hello"
    assert len(loads) == 1


def test_vosk_concurrent_initialization_loads_once(monkeypatch, tmp_path):
    loads = []

    class FakeModel:
        def __init__(self, _path):
            loads.append("load")
            time.sleep(0.02)

    monkeypatch.setitem(
        sys.modules,
        "vosk",
        types.SimpleNamespace(Model=FakeModel, KaldiRecognizer=object),
    )
    monkeypatch.setattr(
        "config.VOSK_MODEL_PATH",
        str(_make_vosk_model_dir(tmp_path)),
    )
    service = STTService("vosk")

    with ThreadPoolExecutor(max_workers=4) as executor:
        models = list(executor.map(lambda _index: service._get_vosk_model(), range(4)))

    assert len(loads) == 1
    assert all(model is models[0] for model in models)


def test_failed_vosk_initialization_can_retry(monkeypatch, tmp_path):
    attempts = []

    class RetryModel:
        def __init__(self, _path):
            attempts.append("attempt")
            if len(attempts) == 1:
                raise RuntimeError("load failed")

    monkeypatch.setitem(
        sys.modules,
        "vosk",
        types.SimpleNamespace(Model=RetryModel, KaldiRecognizer=object),
    )
    monkeypatch.setattr(
        "config.VOSK_MODEL_PATH",
        str(_make_vosk_model_dir(tmp_path)),
    )
    service = STTService("vosk")

    with pytest.raises(RuntimeError, match="load failed"):
        service._get_vosk_model()
    assert service._get_vosk_model() is not None
    assert len(attempts) == 2


def test_stt_status_does_not_load_model(monkeypatch, tmp_path):
    loads = []

    class FakeModel:
        def __init__(self, _path):
            loads.append("load")

    monkeypatch.setitem(
        sys.modules,
        "vosk",
        types.SimpleNamespace(Model=FakeModel, KaldiRecognizer=object),
    )
    monkeypatch.setattr("config.VOSK_MODEL_PATH", str(_make_vosk_model_dir(tmp_path)))

    assert STTService("vosk").status()["available"] is True
    assert loads == []


def test_piper_timeout_uses_configured_deadline(monkeypatch, tmp_path):
    model_path = tmp_path / "voice.onnx"
    model_path.write_bytes(b"model")
    monkeypatch.setattr("config.PIPER_MODEL_PATH", str(model_path))
    monkeypatch.setattr("config.VOICE_TTS_TIMEOUT_SECONDS", 7)
    monkeypatch.setattr("backend.voice.tts_service.shutil.which", lambda _name: "piper")

    def timeout(*_args, **kwargs):
        raise subprocess.TimeoutExpired("piper", kwargs["timeout"])

    monkeypatch.setattr("backend.voice.tts_service.subprocess.run", timeout)

    with pytest.raises(TTSUnavailableError, match="timed out"):
        TTSService._piper("hello")


def test_sapi_timeout_uses_configured_deadline(monkeypatch):
    monkeypatch.setattr("config.VOICE_TTS_TIMEOUT_SECONDS", 4)
    monkeypatch.setattr(TTSService, "_sapi_supported", staticmethod(lambda: True))

    def timeout(*_args, **kwargs):
        raise subprocess.TimeoutExpired("powershell", kwargs["timeout"])

    monkeypatch.setattr("backend.voice.tts_service.subprocess.run", timeout)

    with pytest.raises(TTSUnavailableError, match="timed out"):
        TTSService._sapi("hello")


def test_voice_transcribe_endpoint_is_local_and_protected(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "voice_pipeline",
        LocalVoicePipeline(FakeSTT("hello"), FakeTTS()),
    )
    monkeypatch.setattr(app_module.config, "MEERO_API_KEY", "voice-key")
    client = TestClient(app_module.app)

    unauthorized = client.post(
        "/voice/transcribe",
        files={"audio": ("voice.wav", wav_bytes(), "audio/wav")},
    )
    assert unauthorized.status_code == 401

    response = client.post(
        "/voice/transcribe",
        files={"audio": ("voice.wav", wav_bytes(), "audio/wav")},
        headers={"x-meero-api-key": "voice-key"},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "hello"


def test_voice_endpoint_rejects_remote_requests(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "voice_pipeline",
        LocalVoicePipeline(FakeSTT("hello"), FakeTTS()),
    )
    monkeypatch.setattr(app_module.config, "MEERO_API_KEY", "")
    remote_client = TestClient(app_module.app, client=("203.0.113.10", 5000))

    response = remote_client.post(
        "/voice/transcribe",
        files={"audio": ("voice.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 403
