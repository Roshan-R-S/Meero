"""Local speech-to-text providers."""

from __future__ import annotations

import json
import os
import threading
import wave
from pathlib import Path

import config

from .audio_utils import temporary_wav, validate_wav_bytes


class STTUnavailableError(RuntimeError):
    pass


class STTService:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or getattr(config, "VOICE_STT_PROVIDER", "vosk")).lower()
        self._model_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._vosk_model = None
        self._whisper_model = None

    def status(self) -> dict:
        model_path = self._model_path()
        return {
            "provider": self.provider,
            "available": bool(
                model_path and os.path.exists(model_path) and self._dependency_available()
            ),
            "model_path": os.path.basename(model_path) if model_path else None,
        }

    def transcribe(self, audio: bytes) -> str:
        validate_wav_bytes(audio)
        if self.provider == "vosk":
            return self._transcribe_vosk(audio)
        if self.provider == "faster-whisper":
            return self._transcribe_whisper(audio)
        raise STTUnavailableError(f"Unsupported local STT provider: {self.provider}")

    def _model_path(self) -> str:
        if self.provider == "faster-whisper":
            return getattr(config, "WHISPER_MODEL_PATH", "")
        return getattr(config, "VOSK_MODEL_PATH", "")

    @staticmethod
    def _resolve_vosk_model_path() -> Path:
        configured = Path(config.VOSK_MODEL_PATH)
        candidates = [configured]
        if configured.is_dir():
            candidates.extend(path for path in configured.iterdir() if path.is_dir())
        for candidate in candidates:
            if all((candidate / name).is_dir() for name in ("am", "conf", "graph")):
                return candidate
        return configured

    def _dependency_available(self) -> bool:
        try:
            if self.provider == "vosk":
                import vosk  # noqa: F401
            elif self.provider == "faster-whisper":
                import faster_whisper  # noqa: F401
            else:
                return False
            return True
        except ImportError:
            return False

    def _transcribe_vosk(self, audio: bytes) -> str:
        try:
            from vosk import KaldiRecognizer
        except ImportError as exc:
            raise STTUnavailableError("Vosk is not installed") from exc
        with self._inference_lock:
            model = self._get_vosk_model()
            with temporary_wav(audio) as path, wave.open(str(path), "rb") as wav_file:
                recognizer = KaldiRecognizer(model, wav_file.getframerate())
                while chunk := wav_file.readframes(4000):
                    recognizer.AcceptWaveform(chunk)
                return json.loads(recognizer.FinalResult()).get("text", "").strip()

    def _transcribe_whisper(self, audio: bytes) -> str:
        with self._inference_lock:
            model = self._get_whisper_model()
            with temporary_wav(audio) as path:
                segments, _ = model.transcribe(str(path), language="en")
                return " ".join(segment.text.strip() for segment in segments).strip()

    def _get_vosk_model(self):
        if self._vosk_model is not None:
            return self._vosk_model
        with self._model_lock:
            if self._vosk_model is not None:
                return self._vosk_model
            try:
                from vosk import Model
            except ImportError as exc:
                raise STTUnavailableError("Vosk is not installed") from exc
            model_path = self._resolve_vosk_model_path()
            if not model_path.exists():
                raise STTUnavailableError("Vosk model is not installed")
            model = Model(str(model_path))
            self._vosk_model = model
            return model

    def _get_whisper_model(self):
        if self._whisper_model is not None:
            return self._whisper_model
        with self._model_lock:
            if self._whisper_model is not None:
                return self._whisper_model
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise STTUnavailableError("faster-whisper is not installed") from exc
            model_path = Path(config.WHISPER_MODEL_PATH)
            if not model_path.exists():
                raise STTUnavailableError("Whisper model is not installed")
            model = WhisperModel(str(model_path), device="cpu", compute_type="int8")
            self._whisper_model = model
            return model
