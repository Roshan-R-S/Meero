import json
import types

import config


def make_fake_audio(data=b"fakepcm"):
    class FakeAudio:
        def get_raw_data(self, convert_rate=16000, convert_width=2):
            return data

    return FakeAudio()


def install_fake_tts(monkeypatch, speech_engine):
    monkeypatch.setattr(speech_engine, "pyttsx3", None)


def install_fake_sr(monkeypatch, speech_engine, recognizer):
    class FakeMicrophone:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_sr = types.SimpleNamespace(
        Recognizer=lambda: recognizer,
        Microphone=lambda *args, **kwargs: FakeMicrophone(),
        WaitTimeoutError=TimeoutError,
        UnknownValueError=ValueError,
        RequestError=ConnectionError,
    )
    monkeypatch.setattr(speech_engine, "sr", fake_sr)


def test_listen_vosk_success(monkeypatch, tmp_path):
    # Prepare fake model dir
    model_dir = tmp_path / "vosk-model-small-en-us-0.15"
    for name in ("am", "conf", "graph"):
        (model_dir / name).mkdir(parents=True)
    monkeypatch.setattr(config, "VOSK_MODEL_PATH", str(tmp_path))
    monkeypatch.setattr(config, "SPEECH_RECOGNITION_BACKEND", "vosk")

    # Import inside test to pick up monkeypatched config
    import speech_engine as se
    install_fake_tts(monkeypatch, se)

    # Simulate vosk being available
    monkeypatch.setattr(se, "_has_vosk", True)

    class FakeModel:
        def __init__(self, path):
            assert path.startswith(str(tmp_path))

    class FakeRec:
        def __init__(self, model, rate):
            pass

        def AcceptWaveform(self, data):
            return True

        def Result(self):
            return json.dumps({"text": "hello world"})

    monkeypatch.setattr(se, "Model", FakeModel)
    monkeypatch.setattr(se, "KaldiRecognizer", FakeRec)

    class FakeRecognizer:
        def adjust_for_ambient_noise(self, source, duration=None):
            pass

        def listen(self, source, timeout=None, phrase_time_limit=None):
            return make_fake_audio(b"pcmdata")

    install_fake_sr(monkeypatch, se, FakeRecognizer())

    engine = se.SpeechEngine()
    result = engine.listen()
    assert result == "hello world"


def test_listen_vosk_fallback_to_google(monkeypatch):
    monkeypatch.setattr(config, "SPEECH_RECOGNITION_BACKEND", "vosk")

    import speech_engine as se
    install_fake_tts(monkeypatch, se)

    # Simulate vosk available but recognizer failing
    monkeypatch.setattr(se, "_has_vosk", True)

    class BadRec:
        def __init__(self, model, rate):
            pass

        def AcceptWaveform(self, data):
            raise RuntimeError("decoder error")

    monkeypatch.setattr(se, "Model", lambda path: object())
    monkeypatch.setattr(se, "KaldiRecognizer", BadRec)

    class FakeRecognizer:
        def adjust_for_ambient_noise(self, source, duration=None):
            pass

        def listen(self, source, timeout=None, phrase_time_limit=None):
            return make_fake_audio(b"pcmdata")

        def recognize_google(self, audio, language="en-in"):
            return "Goodbye"

    install_fake_sr(monkeypatch, se, FakeRecognizer())

    engine = se.SpeechEngine()
    result = engine.listen()
    assert result == "goodbye"


def test_listen_google_only(monkeypatch):
    monkeypatch.setattr(config, "SPEECH_RECOGNITION_BACKEND", "google")

    import speech_engine as se
    install_fake_tts(monkeypatch, se)

    class FakeRecognizer:
        def adjust_for_ambient_noise(self, source, duration=None):
            pass

        def listen(self, source, timeout=None, phrase_time_limit=None):
            return make_fake_audio(b"pcmdata")

        def recognize_google(self, audio, language="en-in"):
            return "Testing"

    install_fake_sr(monkeypatch, se, FakeRecognizer())

    engine = se.SpeechEngine()
    result = engine.listen()
    assert result == "testing"
