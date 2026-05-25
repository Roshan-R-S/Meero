"""Microphone-free speech smoke tests for CI."""

import types

import config


class FakeAudio:
    def get_raw_data(self, convert_rate=16000, convert_width=2):
        return b"mock-audio"


class FakeRecognizer:
    def adjust_for_ambient_noise(self, source, duration=None):
        pass

    def listen(self, source, timeout=None, phrase_time_limit=None):
        return FakeAudio()

    def recognize_google(self, audio, language="en-in"):
        return "smoke test command"


class FakeMicrophone:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_google_speech_smoke_without_microphone(monkeypatch):
    import speech_engine

    fake_sr = types.SimpleNamespace(
        Recognizer=lambda: FakeRecognizer(),
        Microphone=lambda *args, **kwargs: FakeMicrophone(),
        WaitTimeoutError=TimeoutError,
        UnknownValueError=ValueError,
        RequestError=ConnectionError,
    )
    monkeypatch.setattr(config, "SPEECH_RECOGNITION_BACKEND", "google")
    monkeypatch.setattr(speech_engine, "pyttsx3", None)
    monkeypatch.setattr(speech_engine, "sr", fake_sr)

    assert speech_engine.SpeechEngine().listen() == "smoke test command"
