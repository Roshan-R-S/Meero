"""Local Piper text-to-speech with Windows SAPI fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import config


class TTSUnavailableError(RuntimeError):
    pass


class TTSService:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or getattr(config, "VOICE_TTS_PROVIDER", "piper")).lower()

    @staticmethod
    def _sapi_supported() -> bool:
        return os.name == "nt"

    def status(self) -> dict:
        piper_available = bool(
            Path(getattr(config, "PIPER_MODEL_PATH", "")).exists()
            and shutil.which(getattr(config, "PIPER_EXECUTABLE", "piper"))
        )
        sapi_available = self._sapi_supported() and shutil.which("powershell") is not None
        return {
            "provider": self.provider,
            "available": piper_available or sapi_available,
            "piper_available": piper_available,
            "sapi_available": sapi_available,
        }

    def synthesize(self, text: str) -> bytes:
        audio, _provider = self.synthesize_with_provider(text)
        return audio

    def synthesize_with_provider(self, text: str) -> tuple[bytes, str]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Synthesis text is empty")
        if self.provider == "piper":
            try:
                return self._piper(clean_text), "piper"
            except TTSUnavailableError:
                if self._sapi_supported():
                    return self._sapi(clean_text), "sapi"
                raise
        if self.provider == "sapi":
            return self._sapi(clean_text), "sapi"
        raise TTSUnavailableError(f"Unsupported local TTS provider: {self.provider}")

    @staticmethod
    def _piper(text: str) -> bytes:
        executable = shutil.which(getattr(config, "PIPER_EXECUTABLE", "piper"))
        model_path = Path(getattr(config, "PIPER_MODEL_PATH", ""))
        if not executable or not model_path.exists():
            raise TTSUnavailableError("Piper executable or model is not installed")
        handle, output_name = tempfile.mkstemp(prefix="meero-tts-", suffix=".wav")
        os.close(handle)
        try:
            subprocess.run(
                [executable, "--model", str(model_path), "--output_file", output_name],
                input=text,
                text=True,
                check=True,
                capture_output=True,
                timeout=getattr(config, "VOICE_TTS_TIMEOUT_SECONDS", 10),
            )
            return Path(output_name).read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise TTSUnavailableError("Piper synthesis timed out") from exc
        finally:
            Path(output_name).unlink(missing_ok=True)

    @staticmethod
    def _sapi(text: str) -> bytes:
        if not TTSService._sapi_supported():
            raise TTSUnavailableError("Windows SAPI is unavailable on this platform")
        handle, output_name = tempfile.mkstemp(prefix="meero-sapi-", suffix=".wav")
        os.close(handle)
        escaped_text = text.replace("'", "''")
        escaped_path = output_name.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SetOutputToWaveFile('{escaped_path}'); $s.Speak('{escaped_text}'); $s.Dispose()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                check=True,
                capture_output=True,
                timeout=getattr(config, "VOICE_TTS_TIMEOUT_SECONDS", 10),
            )
            return Path(output_name).read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise TTSUnavailableError("Windows speech synthesis timed out") from exc
        finally:
            Path(output_name).unlink(missing_ok=True)
