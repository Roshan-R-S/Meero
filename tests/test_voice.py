import io
import wave

import pytest
from fastapi.testclient import TestClient

import backend.app as app_module
from backend.schemas import CommandOutcome
from backend.voice.audio_utils import AudioValidationError, validate_wav_bytes
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
    [b"", b"not-a-wav", wav_bytes(channels=2), wav_bytes(sample_rate=8000), wav_bytes(sample_width=1)],
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
    def status(self):
        return {"provider": "fake", "available": True}

    def synthesize(self, _text):
        return b"RIFFfake"


def test_voice_pipeline_uses_same_command_gateway():
    calls = []
    pipeline = LocalVoicePipeline(FakeSTT(), FakeTTS())

    result = pipeline.execute(
        wav_bytes(),
        lambda text, **kwargs: calls.append((text, kwargs)) or CommandOutcome("Done", "success"),
    )

    assert calls[0][0] == "what time is it"
    assert calls[0][1]["mode"] == "local_voice"
    assert result.audio == b"RIFFfake"


def test_voice_confirmation_requires_spoken_yes():
    pipeline = LocalVoicePipeline(FakeSTT("maybe"), FakeTTS())
    result = pipeline.execute(
        wav_bytes(),
        lambda *_args, **_kwargs: pytest.fail("command must not execute"),
        pending_command="close spotify",
    )
    assert result.outcome.action_status == "confirmation_required"


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


def test_voice_transcribe_endpoint_is_local_and_protected(monkeypatch):
    monkeypatch.setattr(app_module, "voice_pipeline", LocalVoicePipeline(FakeSTT("hello"), FakeTTS()))
    monkeypatch.setattr(app_module.config, "MEERO_API_KEY", "voice-key")
    client = TestClient(app_module.app)

    unauthorized = client.post("/voice/transcribe", files={"audio": ("voice.wav", wav_bytes(), "audio/wav")})
    assert unauthorized.status_code == 401

    response = client.post(
        "/voice/transcribe",
        files={"audio": ("voice.wav", wav_bytes(), "audio/wav")},
        headers={"x-meero-api-key": "voice-key"},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "hello"


def test_voice_endpoint_rejects_remote_requests(monkeypatch):
    monkeypatch.setattr(app_module, "voice_pipeline", LocalVoicePipeline(FakeSTT("hello"), FakeTTS()))
    monkeypatch.setattr(app_module.config, "MEERO_API_KEY", "")
    remote_client = TestClient(app_module.app, client=("203.0.113.10", 5000))

    response = remote_client.post(
        "/voice/transcribe",
        files={"audio": ("voice.wav", wav_bytes(), "audio/wav")},
    )

    assert response.status_code == 403
