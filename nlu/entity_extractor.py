"""Minimal entity extraction helpers shared by safety and routing."""

from __future__ import annotations

OPEN_VERBS = ("open", "launch", "start", "run")
CLOSE_VERBS = ("close", "kill", "stop", "quit", "exit")


def extract_app_name(text: str, *, close: bool = False) -> str:
    app_name = text
    verbs = CLOSE_VERBS if close else OPEN_VERBS
    for phrase in (*verbs, "please", "can you", "could you", "the"):
        app_name = app_name.replace(phrase, "")
    return app_name.strip()
