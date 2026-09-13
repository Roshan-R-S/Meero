"""Local neural text-to-speech with XTTS v2 voice cloning, Piper, and Windows SAPI fallback."""

from __future__ import annotations

import base64
import concurrent.futures
import io
import logging
import os
import pickle
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# Ensure torchaudio uses soundfile on Windows/environments without torchcodec
try:
    import soundfile as sf
    import torch
    import torchaudio

    _orig_load = getattr(torchaudio, "load", None)

    def _safe_load(
        uri,
        frame_offset: int = 0,
        num_frames: int = -1,
        normalize: bool = True,
        channels_first: bool = True,
        format: str | None = None,
        buffer_size: int = 4096,
        backend: str | None = None,
        **kwargs,
    ) -> tuple[torch.Tensor, int]:
        try:
            if _orig_load:
                return _orig_load(
                    uri,
                    frame_offset=frame_offset,
                    num_frames=num_frames,
                    normalize=normalize,
                    channels_first=channels_first,
                    format=format,
                    buffer_size=buffer_size,
                    backend=backend,
                    **kwargs,
                )
        except Exception:
            pass
        data, sr = sf.read(
            uri,
            start=frame_offset,
            stop=None if (num_frames is None or num_frames == -1) else frame_offset + num_frames,
            dtype="float32",
        )
        tensor = torch.from_numpy(data)
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        elif channels_first:
            tensor = tensor.t()
        return tensor, int(sr)

    setattr(torchaudio, "load", _safe_load)
except Exception:
    pass


class TTSUnavailableError(RuntimeError):
    pass


def split_text_into_chunks(text: str, min_chars: int = 40, max_chars: int = 180) -> list[str]:
    """Split text into sentence or short phrase chunks on natural punctuation boundaries."""
    import re
    cleaned = text.strip()
    if not cleaned:
        return []

    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?;\n])\s+', cleaned) if s.strip()]
    if len(raw_sentences) <= 1:
        if len(cleaned) <= max_chars:
            return [cleaned]

    chunks = []
    current_chunk = ""

    for sentence in raw_sentences:
        if len(sentence) > max_chars:
            clauses = [c.strip() for c in re.split(r'(?<=[,:\-\—])\s+', sentence) if c.strip()]
            for clause in clauses:
                if not current_chunk:
                    current_chunk = clause
                elif len(current_chunk) + len(clause) + 1 <= max_chars:
                    current_chunk += " " + clause
                else:
                    chunks.append(current_chunk)
                    current_chunk = clause
        else:
            if not current_chunk:
                current_chunk = sentence
            elif len(current_chunk) + len(sentence) + 1 <= max_chars:
                if len(current_chunk) < min_chars:
                    current_chunk += " " + sentence
                else:
                    chunks.append(current_chunk)
                    current_chunk = sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [cleaned]


class TTSService:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or getattr(config, "VOICE_TTS_PROVIDER", "piper")).lower()
        self._model_lock = threading.Lock()
        self._xtts_model = None
        self._xtts_latents = None
        self._xtts_latents_key = None
        self._warmup_loading = False
        self._warmup_latency_ms = None
        self._warmup_error = None

    @staticmethod
    def _sapi_supported() -> bool:
        return os.name == "nt"

    def _xtts_dependency_available(self) -> bool:
        try:
            import torch  # noqa: F401
            import TTS  # noqa: F401
            return True
        except ImportError:
            return False

    def readiness_status(self) -> dict:
        piper_available = bool(
            Path(getattr(config, "PIPER_MODEL_PATH", "")).exists()
            and shutil.which(getattr(config, "PIPER_EXECUTABLE", "piper"))
        )
        sapi_available = self._sapi_supported() and shutil.which("powershell") is not None
        is_ready = False
        status_str = "idle"

        if self.provider == "xtts":
            if self._xtts_model is not None and self._xtts_latents is not None:
                is_ready = True
                status_str = "ready"
            elif self._warmup_loading:
                status_str = "loading"
            elif self._warmup_error:
                status_str = "error"
            elif self._xtts_dependency_available():
                status_str = "idle"
            else:
                status_str = "missing"
        elif self.provider == "piper":
            is_ready = piper_available
            status_str = "ready" if piper_available else "missing"
        elif self.provider == "sapi":
            is_ready = sapi_available
            status_str = "ready" if sapi_available else "unavailable"

        return {
            "status": status_str,
            "ready": is_ready,
            "provider": self.provider,
            "latents_cached": self._xtts_latents is not None,
            "warmup_latency_ms": self._warmup_latency_ms,
            "message": self._warmup_error or "",
        }

    def status(self) -> dict:
        piper_available = bool(
            Path(getattr(config, "PIPER_MODEL_PATH", "")).exists()
            and shutil.which(getattr(config, "PIPER_EXECUTABLE", "piper"))
        )
        sapi_available = self._sapi_supported() and shutil.which("powershell") is not None
        ref_audios = getattr(config, "VOICE_CLONE_REFERENCE_AUDIOS", [])
        xtts_available = bool(self._xtts_dependency_available() and ref_audios)

        available = False
        if self.provider == "xtts":
            available = xtts_available or piper_available or sapi_available
        elif self.provider == "piper":
            available = piper_available or sapi_available
        elif self.provider == "sapi":
            available = sapi_available

        return {
            "provider": self.provider,
            "available": available,
            "xtts_available": xtts_available,
            "piper_available": piper_available,
            "sapi_available": sapi_available,
            "reference_audios": [os.path.basename(p) for p in ref_audios],
            "readiness": self.readiness_status(),
        }

    def synthesize(self, text: str) -> bytes:
        audio, _provider = self.synthesize_with_provider(text)
        return audio

    def synthesize_with_provider(self, text: str, fast_ack: bool = False) -> tuple[bytes, str]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Synthesis text is empty")

        fast_ack_enabled = getattr(config, "VOICE_FAST_ACK_ENABLED", True)
        low_latency = getattr(config, "VOICE_LOW_LATENCY_MODE", False)
        # Only use fast-ack if enabled in config and either explicitly requested or XTTS is actively warming up
        should_fast_ack = fast_ack_enabled and (
            fast_ack or (low_latency and self.provider == "xtts" and self._warmup_loading)
        )

        if should_fast_ack:
            ack_provider = getattr(config, "VOICE_FAST_ACK_PROVIDER", "piper").lower()
            if ack_provider == "piper":
                try:
                    return self._piper(clean_text), "piper"
                except TTSUnavailableError:
                    if self._sapi_supported():
                        return self._sapi(clean_text), "sapi"
            elif ack_provider == "sapi":
                if self._sapi_supported():
                    try:
                        return self._sapi(clean_text), "sapi"
                    except TTSUnavailableError:
                        pass
                try:
                    return self._piper(clean_text), "piper"
                except TTSUnavailableError:
                    pass

        if self.provider == "xtts":
            try:
                return self._xtts(clean_text), "xtts"
            except (TTSUnavailableError, Exception) as exc:
                logger.warning("XTTS synthesis unavailable or failed (%s); trying fallback providers", exc)
                try:
                    return self._piper(clean_text), "piper"
                except TTSUnavailableError:
                    if self._sapi_supported():
                        return self._sapi(clean_text), "sapi"
                    raise

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

    def synthesize_stream(
        self,
        text: str,
        min_chars: int | None = None,
        max_chars: int | None = None,
        fast_ack: bool = False,
    ):
        """Yield (chunk_index, total_chunks, audio_bytes, selected_provider) for each chunk."""
        min_c = min_chars or getattr(config, "VOICE_STREAM_CHUNK_MIN_CHARS", 60)
        max_c = max_chars or getattr(config, "VOICE_STREAM_CHUNK_MAX_CHARS", 180)
        chunks = split_text_into_chunks(text, min_chars=min_c, max_chars=max_c)
        if not chunks:
            chunks = [text.strip()]
        chunks = [c for c in chunks if c.strip()]
        total = len(chunks)
        if total == 0:
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(total, 3)) as pool:
            futures = [
                pool.submit(self.synthesize_with_provider, chunk, fast_ack=(fast_ack and i == 0))
                for i, chunk in enumerate(chunks)
            ]
            for idx, future in enumerate(futures):
                audio, provider = future.result()
                yield idx, total, audio, provider

    def _get_xtts_model(self):
        if self._xtts_model is not None:
            return self._xtts_model

        with self._model_lock:
            if self._xtts_model is not None:
                return self._xtts_model

            if not self._xtts_dependency_available():
                raise TTSUnavailableError("Coqui TTS or PyTorch is not installed in the environment.")

            try:
                import torch
                from TTS.api import TTS

                use_gpu_config = getattr(config, "XTTS_USE_GPU", "auto")
                if use_gpu_config == "true":
                    use_gpu = torch.cuda.is_available()
                elif use_gpu_config == "false":
                    use_gpu = False
                else:
                    use_gpu = torch.cuda.is_available()

                model_dir = Path(getattr(config, "XTTS_MODEL_DIR", ""))
                if model_dir.exists() and (model_dir / "config.json").exists():
                    logger.info("Loading local XTTS v2 model from directory: %s", model_dir)
                    tts = TTS(model_path=str(model_dir), config_path=str(model_dir / "config.json"), gpu=use_gpu)
                else:
                    logger.info("Initializing XTTS v2 model...")
                    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)

                self._xtts_model = tts
                return self._xtts_model
            except Exception as exc:
                raise TTSUnavailableError(f"Failed loading XTTS model: {exc}") from exc

    def _get_xtts_latents(self, model, valid_refs):
        key = tuple(valid_refs)
        if self._xtts_latents is not None and self._xtts_latents_key == key:
            return self._xtts_latents

        latents_cache_path = os.path.join(
            getattr(config, "LOCAL_TTS_DIR", "models/local-tts"),
            "latents_cache.pkl",
        )

        with self._model_lock:
            if self._xtts_latents is not None and self._xtts_latents_key == key:
                return self._xtts_latents

            if os.path.exists(latents_cache_path) and valid_refs:
                try:
                    cache_mtime = os.path.getmtime(latents_cache_path)
                    refs_mtime = max(os.path.getmtime(r) for r in valid_refs if os.path.exists(r))
                    if cache_mtime > refs_mtime:
                        with open(latents_cache_path, "rb") as f:
                            self._xtts_latents = pickle.load(f)
                            self._xtts_latents_key = key
                            logger.info("Loaded XTTS latents from disk cache: %s", latents_cache_path)
                            return self._xtts_latents
                except Exception as exc:
                    logger.warning("Failed loading XTTS latents cache: %s", exc)

            trimmed_refs = []
            temp_files = []
            for ref_path in valid_refs:
                try:
                    info = sf.info(ref_path)
                    stop_sample = int(10 * info.samplerate)
                    data, sr = sf.read(ref_path, stop=stop_sample, dtype="float32")
                    temp_f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_f.close()
                    sf.write(temp_f.name, data, sr)
                    trimmed_refs.append(temp_f.name)
                    temp_files.append(temp_f.name)
                except Exception:
                    trimmed_refs.append(ref_path)

            try:
                tts_model = getattr(getattr(model, "synthesizer", None), "tts_model", None)
                if tts_model is not None and hasattr(tts_model, "get_conditioning_latents"):
                    res = tts_model.get_conditioning_latents(audio_path=trimmed_refs)
                    if isinstance(res, (tuple, list)) and len(res) == 2:
                        self._xtts_latents = res
                        self._xtts_latents_key = key
                        logger.info("XTTS speaker conditioning latents cached successfully.")
                        try:
                            os.makedirs(os.path.dirname(latents_cache_path), exist_ok=True)
                            with open(latents_cache_path, "wb") as f:
                                pickle.dump(self._xtts_latents, f)
                            logger.info("Saved XTTS latents to disk cache: %s", latents_cache_path)
                        except Exception as exc:
                            logger.warning("Failed writing XTTS latents cache: %s", exc)
            except Exception:
                pass
            finally:
                for tf in temp_files:
                    Path(tf).unlink(missing_ok=True)

            return self._xtts_latents

    def _xtts(self, text: str) -> bytes:
        ref_audios = getattr(config, "VOICE_CLONE_REFERENCE_AUDIOS", [])
        if not ref_audios:
            raise TTSUnavailableError("No reference voice audio files found for voice cloning.")

        valid_refs = [str(Path(p).resolve()) for p in ref_audios if Path(p).exists()]
        if not valid_refs:
            raise TTSUnavailableError(f"None of the configured reference audios exist: {ref_audios}")

        model = self._get_xtts_model()
        language = getattr(config, "XTTS_LANGUAGE", "en")

        try:
            latents = self._get_xtts_latents(model, valid_refs)
            tts_model = getattr(getattr(model, "synthesizer", None), "tts_model", None)

            if (
                latents is not None
                and isinstance(latents, (tuple, list))
                and len(latents) == 2
                and tts_model is not None
                and hasattr(tts_model, "inference")
            ):
                gpt_latents, speaker_emb = latents
                out = tts_model.inference(
                    text=text,
                    language=language,
                    gpt_cond_latent=gpt_latents,
                    speaker_embedding=speaker_emb,
                    temperature=0.7,
                    repetition_penalty=2.0,
                    speed=1.0,
                    enable_text_splitting=True,
                )
                wav = out["wav"]
                if hasattr(wav, "cpu"):
                    wav = wav.cpu().numpy()
                buf = io.BytesIO()
                sf.write(buf, wav, 24000, format="WAV")
                return buf.getvalue()

            # Fallback to standard tts_to_file
            handle, output_name = tempfile.mkstemp(prefix="meero-xtts-", suffix=".wav")
            os.close(handle)
            try:
                model.tts_to_file(
                    text=text,
                    speaker_wav=valid_refs if len(valid_refs) > 1 else valid_refs[0],
                    language=language,
                    file_path=output_name,
                )
                return Path(output_name).read_bytes()
            finally:
                Path(output_name).unlink(missing_ok=True)
        except Exception as exc:
            raise TTSUnavailableError(f"XTTS synthesis error: {exc}") from exc

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
                timeout=getattr(config, "VOICE_TTS_TIMEOUT_SECONDS", 15),
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
        text_handle, text_name = tempfile.mkstemp(prefix="meero-sapi-txt-", suffix=".txt")
        with os.fdopen(text_handle, "w", encoding="utf-8") as f:
            f.write(text)

        escaped_path = output_name.replace("'", "''")
        escaped_text_path = text_name.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.SetOutputToWaveFile('{escaped_path}'); "
            f"$txt = [System.IO.File]::ReadAllText('{escaped_text_path}', [System.Text.Encoding]::UTF8); "
            "$s.Speak($txt); $s.Dispose();"
        )
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
                check=True,
                capture_output=True,
                timeout=getattr(config, "VOICE_TTS_TIMEOUT_SECONDS", 15),
            )
            return Path(output_name).read_bytes()
        except subprocess.TimeoutExpired as exc:
            raise TTSUnavailableError("Windows speech synthesis timed out") from exc
        finally:
            Path(output_name).unlink(missing_ok=True)
            Path(text_name).unlink(missing_ok=True)
