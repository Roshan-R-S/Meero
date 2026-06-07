"""Build deterministic-routing text without modifying the raw user text."""

from __future__ import annotations

from .asr_corrections import apply_asr_corrections
from .normalizer import normalize_text
from .wake_word import strip_wake_word


def prepare_routing_text(text: str) -> str:
    normalized = normalize_text(text)
    without_wake_word = strip_wake_word(normalized)
    return apply_asr_corrections(without_wake_word)
