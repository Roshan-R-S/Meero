"""Voice API request and response contracts."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SynthesisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=5000)


class TranscriptionResponse(BaseModel):
    transcript: str
    provider: str


class VoiceCommandResponse(BaseModel):
    transcript: str
    response: str
    action_status: str
    sentiment: str = "neutral"
    pending_command: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    audio_base64: Optional[str] = None
    audio_mime_type: Optional[str] = None
