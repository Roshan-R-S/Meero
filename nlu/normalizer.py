"""Conservative text normalization used only by deterministic routing."""

from __future__ import annotations

import re

_PUNCTUATION_RE = re.compile(r"[.,!?;:'\"]+")
_WHITESPACE_RE = re.compile(r"\s+")


CONFIRM_WORDS = frozenset(["yes", "y", "yeah", "yep", "ok", "okay", "confirm", "proceed", "do it"])
CANCEL_WORDS = frozenset(["no", "n", "nope", "cancel", "stop", "don't", "do not"])


def normalize_text(text: str) -> str:
    normalized = _PUNCTUATION_RE.sub(" ", text.lower())
    return _WHITESPACE_RE.sub(" ", normalized).strip()
