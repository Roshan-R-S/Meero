"""Audio to command to optional local-audio response."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.schemas import CommandOutcome
from nlu.normalizer import normalize_text

from .stt_service import STTService
from .tts_service import TTSService, TTSUnavailableError


@dataclass
class VoicePipelineResult:
    transcript: str
    outcome: object
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

    def execute(
        self,
        audio: bytes,
        command_fn: Callable,
        *,
        synthesize: bool = True,
        **command_kwargs,
    ) -> VoicePipelineResult:
        transcript = self.transcribe(audio)
        if not transcript.strip():
            raise ValueError("No speech was recognized")
        pending_command = command_kwargs.get("pending_command")
        if pending_command and not command_kwargs.get("confirm"):
            normalized = normalize_text(transcript)
            if normalized in {"yes", "y", "yeah", "yep", "ok", "okay", "confirm", "proceed", "do it"}:
                command_kwargs["confirm"] = True
            elif normalized in {"no", "n", "nope", "cancel", "stop", "do not", "don t"}:
                return VoicePipelineResult(
                    transcript=transcript,
                    outcome=CommandOutcome(
                        response="Action cancelled.",
                        action_status="cancelled",
                        pending_command=None,
                        metadata={"engine": "voice_confirmation"},
                    ),
                )
            else:
                return VoicePipelineResult(
                    transcript=transcript,
                    outcome=CommandOutcome(
                        response="Please say yes to continue or no to cancel.",
                        action_status="confirmation_required",
                        pending_command=pending_command,
                        metadata={"engine": "voice_confirmation"},
                    ),
                )
        outcome = command_fn(transcript, mode="local_voice", **command_kwargs)
        response_audio = None
        if synthesize:
            try:
                response_audio = self.synthesize(outcome.response)
            except TTSUnavailableError:
                response_audio = None
        return VoicePipelineResult(transcript=transcript, outcome=outcome, audio=response_audio)
