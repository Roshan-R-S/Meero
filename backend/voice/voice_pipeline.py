"""Audio to command to optional local-audio response."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Callable

from backend.schemas import CommandOutcome
from nlu.normalizer import normalize_text

from .stt_service import STTService
from .tts_service import TTSService, TTSUnavailableError

logger = logging.getLogger(__name__)


@dataclass
class VoicePipelineResult:
    transcript: str
    outcome: CommandOutcome
    audio: bytes | None = None


class LocalVoicePipeline:
    def __init__(self, stt: STTService | None = None, tts: TTSService | None = None):
        self.stt = stt or STTService()
        self.tts = tts or TTSService()

    def status(self) -> dict:
        return {"stt": self.stt.status(), "tts": self.tts.status()}

    def transcribe(self, audio: bytes) -> str:
        return self.stt.transcribe(audio)

    def synthesize(self, text: str) -> bytes:
        return self.tts.synthesize(text)

    def synthesize_with_provider(self, text: str) -> tuple[bytes, str]:
        synthesize_with_provider = getattr(self.tts, "synthesize_with_provider", None)
        if synthesize_with_provider is not None:
            return synthesize_with_provider(text)
        return self.synthesize(text), getattr(self.tts, "provider", "unknown")

    def execute(
        self,
        audio: bytes,
        command_fn: Callable,
        *,
        synthesize: bool = True,
        **command_kwargs,
    ) -> VoicePipelineResult:
        stt_started = time.perf_counter()
        transcript = self.transcribe(audio)
        stt_step = self._trace_step(
            "stt",
            "selected",
            provider=getattr(self.stt, "provider", "unknown"),
            latency_ms=self._elapsed_ms(stt_started),
        )
        if not transcript.strip():
            raise ValueError("No speech was recognized")
        pending_command = command_kwargs.get("pending_command")
        confirmation_step = None
        outcome = None
        if pending_command and not command_kwargs.get("confirm"):
            normalized = normalize_text(transcript)
            if normalized in {
                "yes",
                "y",
                "yeah",
                "yep",
                "ok",
                "okay",
                "confirm",
                "proceed",
                "do it",
            }:
                command_kwargs["confirm"] = True
                confirmation_step = self._trace_step("voice_confirmation", "confirmed")
            elif normalized in {"no", "n", "nope", "cancel", "stop", "do not", "don t"}:
                outcome = CommandOutcome(
                    response="Action cancelled.",
                    action_status="cancelled",
                    pending_command=None,
                    metadata={"engine": "voice_confirmation"},
                )
                confirmation_step = self._trace_step("voice_confirmation", "cancelled")
            else:
                outcome = CommandOutcome(
                    response="Please say yes to continue or no to cancel.",
                    action_status="confirmation_required",
                    pending_command=pending_command,
                    metadata={"engine": "voice_confirmation"},
                )
                confirmation_step = self._trace_step("voice_confirmation", "confirmation_required")

        if outcome is None:
            outcome = command_fn(transcript, mode="local_voice", **command_kwargs)

        response_audio = None
        if synthesize:
            tts_started = time.perf_counter()
            try:
                response_audio, selected_provider = self.synthesize_with_provider(outcome.response)
                tts_step = self._trace_step(
                    "tts",
                    "selected",
                    provider=selected_provider,
                    latency_ms=self._elapsed_ms(tts_started),
                )
            except TTSUnavailableError as exc:
                response_audio = None
                reason = "timeout" if "timed out" in str(exc).lower() else "provider_unavailable"
                tts_step = self._trace_step(
                    "tts",
                    "unavailable",
                    provider=getattr(self.tts, "provider", "unknown"),
                    reason=reason,
                    latency_ms=self._elapsed_ms(tts_started),
                )
        else:
            tts_step = self._trace_step(
                "tts",
                "skipped",
                provider=getattr(self.tts, "provider", "unknown"),
                reason="disabled",
            )

        existing_trace = list(outcome.metadata.get("decision_trace", []))
        prefix = [stt_step]
        if confirmation_step is not None:
            prefix.append(confirmation_step)
        outcome.metadata["decision_trace"] = [*prefix, *existing_trace, tts_step]
        return VoicePipelineResult(transcript=transcript, outcome=outcome, audio=response_audio)

    def execute_stream(
        self,
        audio: bytes,
        command_fn: Callable,
        *,
        synthesize: bool = True,
        audio_mode: str = "chunked",
        fast_ack: bool = False,
        **command_kwargs,
    ):
        """Yield real-time NDJSON event dictionaries across STT, routing, text, and TTS chunking."""
        import base64

        logger.info("[Voice Stream] Received audio input (%d bytes)", len(audio))
        stt_started = time.perf_counter()
        try:
            transcript = self.transcribe(audio)
        except Exception as exc:
            logger.error("[Voice Stream] Transcription error: %s", exc)
            yield {"type": "error", "message": f"Transcription error: {exc}"}
            return

        stt_latency = self._elapsed_ms(stt_started)
        stt_step = self._trace_step(
            "stt",
            "selected",
            provider=getattr(self.stt, "provider", "unknown"),
            latency_ms=stt_latency,
        )
        yield {"type": "trace", **stt_step}

        if not transcript.strip():
            logger.warning("[Voice Stream] Empty transcript from STT (in %.1fms). No speech was recognized.", stt_latency)
            yield {"type": "error", "message": "No speech was recognized"}
            return

        logger.info("[Voice Stream] Transcribed: '%s' in %.1fms", transcript, stt_latency)
        yield {"type": "transcript", "text": transcript}

        pending_command = command_kwargs.get("pending_command")
        confirmation_step = None
        outcome = None

        if pending_command and not command_kwargs.get("confirm"):
            normalized = normalize_text(transcript)
            if normalized in {
                "yes",
                "y",
                "yeah",
                "yep",
                "ok",
                "okay",
                "confirm",
                "proceed",
                "do it",
            }:
                command_kwargs["confirm"] = True
                confirmation_step = self._trace_step("voice_confirmation", "confirmed")
            elif normalized in {"no", "n", "nope", "cancel", "stop", "do not", "don t"}:
                outcome = CommandOutcome(
                    response="Action cancelled.",
                    action_status="cancelled",
                    pending_command=None,
                    metadata={"engine": "voice_confirmation"},
                )
                confirmation_step = self._trace_step("voice_confirmation", "cancelled")
            else:
                outcome = CommandOutcome(
                    response="Please say yes to continue or no to cancel.",
                    action_status="confirmation_required",
                    pending_command=pending_command,
                    metadata={"engine": "voice_confirmation"},
                )
                confirmation_step = self._trace_step("voice_confirmation", "confirmation_required")

        if confirmation_step is not None:
            yield {"type": "trace", **confirmation_step}

        if outcome is None:
            try:
                outcome = command_fn(transcript, mode="local_voice", **command_kwargs)
            except Exception as exc:
                logger.error("[Voice Stream] Command error: %s", exc)
                yield {"type": "error", "message": f"Command error: {exc}"}
                return

        logger.info(
            "[Voice Stream] Command response: '%s' (engine=%s, status=%s)",
            outcome.response,
            outcome.metadata.get("engine", "unknown"),
            outcome.action_status,
        )

        for step in outcome.metadata.get("decision_trace", []):
            yield {"type": "trace", **step}

        yield {
            "type": "text_final",
            "transcript": transcript,
            "response": outcome.response,
            "action_status": outcome.action_status,
            "sentiment": getattr(outcome, "sentiment", "neutral"),
            "pending_command": outcome.pending_command,
            "metadata": outcome.metadata,
        }

        if synthesize and audio_mode != "none" and outcome.response:
            tts_started = time.perf_counter()
            tts_prov = getattr(self.tts, "provider", "unknown")
            logger.info("[Voice Stream] Starting TTS synthesis with provider '%s' (fast_ack=%s)...", tts_prov, fast_ack)
            try:
                if hasattr(self.tts, "synthesize_stream"):
                    for idx, total, chunk_audio, prov in self.tts.synthesize_stream(
                        outcome.response, fast_ack=fast_ack
                    ):
                        b64 = base64.b64encode(chunk_audio).decode("ascii")
                        logger.info("[Voice Stream] Yielding audio chunk %d/%d (%d bytes, provider=%s)", idx + 1, total, len(chunk_audio), prov)
                        yield {
                            "type": "audio_chunk",
                            "index": idx,
                            "total": total,
                            "audio_base64": b64,
                            "mime_type": "audio/wav",
                            "provider": prov,
                        }
                else:
                    audio_data, prov = self.synthesize_with_provider(outcome.response)
                    b64 = base64.b64encode(audio_data).decode("ascii")
                    logger.info("[Voice Stream] Yielding single audio chunk (%d bytes, provider=%s)", len(audio_data), prov)
                    yield {
                        "type": "audio_chunk",
                        "index": 0,
                        "total": 1,
                        "audio_base64": b64,
                        "mime_type": "audio/wav",
                        "provider": prov,
                    }
                tts_lat = self._elapsed_ms(tts_started)
                logger.info("[Voice Stream] All TTS synthesis complete in %.1fms", tts_lat)
                yield {
                    "type": "trace",
                    "stage": "tts",
                    "status": "selected",
                    "latency_ms": tts_lat,
                }
            except Exception as exc:
                logger.error("[Voice Stream] TTS synthesis failed: %s", exc)
                reason = "timeout" if "timed out" in str(exc).lower() else "provider_unavailable"
                yield {
                    "type": "trace",
                    "stage": "tts",
                    "status": "unavailable",
                    "reason": reason,
                    "latency_ms": self._elapsed_ms(tts_started),
                }

        yield {"type": "done"}

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1000

    @staticmethod
    def _trace_step(stage: str, status: str, **details) -> dict:
        return {
            "stage": stage,
            "status": status,
            **{key: value for key, value in details.items() if value is not None},
        }
