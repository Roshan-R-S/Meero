"""Validation and request-scoped storage for local WAV audio."""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import config


class AudioValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    channels: int
    sample_width: int
    sample_rate: int
    frames: int
    duration_seconds: float


def validate_wav_bytes(audio: bytes) -> AudioInfo:
    if not audio:
        raise AudioValidationError("Audio upload is empty")
    if len(audio) > getattr(config, "VOICE_MAX_UPLOAD_BYTES", 10 * 1024 * 1024):
        raise AudioValidationError("Audio upload exceeds the configured size limit")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav_file:
            info = AudioInfo(
                channels=wav_file.getnchannels(),
                sample_width=wav_file.getsampwidth(),
                sample_rate=wav_file.getframerate(),
                frames=wav_file.getnframes(),
                duration_seconds=wav_file.getnframes() / max(wav_file.getframerate(), 1),
            )
            compression = wav_file.getcomptype()
    except (wave.Error, EOFError) as exc:
        raise AudioValidationError("Audio must be a valid PCM WAV file") from exc

    if compression != "NONE":
        raise AudioValidationError("Audio must use uncompressed PCM")
    if info.channels != 1:
        raise AudioValidationError("Audio must be mono")
    if info.sample_width != 2:
        raise AudioValidationError("Audio must use 16-bit samples")
    if info.sample_rate != 16000:
        raise AudioValidationError("Audio must use a 16000 Hz sample rate")
    if info.frames <= 0:
        raise AudioValidationError("Audio contains no samples")
    if info.duration_seconds > getattr(config, "VOICE_MAX_DURATION_SECONDS", 30.0):
        raise AudioValidationError("Audio exceeds the configured duration limit")
    return info


@contextlib.contextmanager
def temporary_wav(audio: bytes) -> Iterator[Path]:
    validate_wav_bytes(audio)
    handle, path = tempfile.mkstemp(prefix="meero-voice-", suffix=".wav")
    try:
        with os.fdopen(handle, "wb") as wav_file:
            wav_file.write(audio)
        yield Path(path)
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
