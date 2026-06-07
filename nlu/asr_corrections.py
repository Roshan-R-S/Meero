"""Small, explicit ASR correction table for deterministic routes."""

from __future__ import annotations

ASR_CORRECTIONS = {
    "visual studio coat": "visual studio code",
    "cal cue later": "calculator",
    "note pad": "notepad",
    "spot if eye": "spotify",
    "screen shot": "screenshot",
}


def apply_asr_corrections(text: str) -> str:
    corrected = text
    for heard, intended in ASR_CORRECTIONS.items():
        corrected = corrected.replace(heard, intended)
    return corrected
