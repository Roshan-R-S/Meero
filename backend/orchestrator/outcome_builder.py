"""Build consistent command outcomes from orchestrator decisions."""

from __future__ import annotations

from typing import Optional

from backend.schemas import CommandOutcome

from .decision_trace import DecisionTrace


class OutcomeBuilder:
    @staticmethod
    def build(
        response: str,
        action_status: str,
        *,
        sentiment: str = "neutral",
        pending_command: Optional[str] = None,
        metadata: Optional[dict] = None,
        trace: Optional[DecisionTrace] = None,
    ) -> CommandOutcome:
        result_metadata = dict(metadata or {})
        if trace is not None:
            result_metadata["decision_trace"] = trace.to_list()
        return CommandOutcome(
            response=response,
            action_status=action_status,
            sentiment=sentiment,
            pending_command=pending_command,
            metadata=result_metadata,
        )
