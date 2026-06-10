"""Execution context shared by every command entry point."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nlu.intent_router import prepare_routing_text


@dataclass(frozen=True)
class ExecutionContext:
    raw_text: str
    routing_text: str
    mode: str = "voice"
    client_is_local: bool = True
    confirm: bool = False
    pending_command: Optional[str] = None

    @classmethod
    def build(
        cls,
        query: str,
        *,
        mode: str = "voice",
        client_is_local: bool = True,
        confirm: bool = False,
        pending_command: Optional[str] = None,
    ) -> "ExecutionContext":
        raw_text = (pending_command or query).strip()
        return cls(
            raw_text=raw_text,
            routing_text=prepare_routing_text(raw_text),
            mode=mode,
            client_is_local=client_is_local,
            confirm=confirm,
            pending_command=pending_command,
        )
