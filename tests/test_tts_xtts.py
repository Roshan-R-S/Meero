"""Unit tests for XTTS v2 voice cloning provider and multi-reference audio handling."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

import config
from backend.voice.tts_service import TTSService, TTSUnavailableError


def test_reference_audios_resolution():
    """Verify that both reference audios are detected by config."""
    refs = config.VOICE_CLONE_REFERENCE_AUDIOS
    assert len(refs) >= 2
    filenames = [os.path.basename(p) for p in refs]
    assert "reference.wav" in filenames
    assert "reference1.wav" in filenames


def test_xtts_status():
    """Verify TTSService.status reports reference audios and xtts provider."""
    service = TTSService(provider="xtts")
    st = service.status()
    assert st["provider"] == "xtts"
    assert "reference_audios" in st
    assert "reference.wav" in st["reference_audios"]
    assert "reference1.wav" in st["reference_audios"]


def test_xtts_synthesis_with_mock(monkeypatch, tmp_path):
    """Verify XTTS synthesizes audio using the multi-reference speaker WAVs."""
    mock_tts_instance = MagicMock()

    def fake_tts_to_file(text, speaker_wav, language, file_path):
        assert text == "Hello boss"
        assert isinstance(speaker_wav, list)
        assert len(speaker_wav) >= 2
        # Write dummy WAV bytes
        Path(file_path).write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00")

    mock_tts_instance.tts_to_file = fake_tts_to_file

    service = TTSService(provider="xtts")
    service._xtts_model = mock_tts_instance

    audio_bytes, provider = service.synthesize_with_provider("Hello boss")
    assert provider == "xtts"
    assert audio_bytes.startswith(b"RIFF")


def test_xtts_fallback_to_sapi_when_model_unavailable(monkeypatch):
    """Verify that if XTTS fails, it falls back to SAPI when SAPI is available."""
    service = TTSService(provider="xtts")
    monkeypatch.setattr(service, "_xtts_dependency_available", lambda: False)
    monkeypatch.setattr(TTSService, "_sapi_supported", staticmethod(lambda: True))
    monkeypatch.setattr(TTSService, "_sapi", staticmethod(lambda text: b"RIFF_SAPI_DUMMY"))

    audio_bytes, provider = service.synthesize_with_provider("Fallback test")
    assert provider == "sapi"
    assert audio_bytes == b"RIFF_SAPI_DUMMY"


def test_empty_text_raises_value_error():
    service = TTSService(provider="xtts")
    with pytest.raises(ValueError, match="Synthesis text is empty"):
        service.synthesize("   ")
