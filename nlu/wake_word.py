"""Wake-word variants and deterministic stripping helpers."""

from __future__ import annotations

WAKE_WORD_VARIANTS = (
    "hey meero",
    "hey miro",
    "a meero",
    "hey mirror",
    "hey nero",
    "hey mero",
    "hey mira",
    "hey mural",
    "meero",
    "miro",
)


def strip_wake_word(text: str) -> str:
    stripped = text
    for variant in sorted(WAKE_WORD_VARIANTS, key=len, reverse=True):
        if stripped.startswith(variant):
            stripped = stripped[len(variant) :].strip()
            break
    return stripped
