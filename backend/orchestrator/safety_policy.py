"""Local-first safety checks applied before deterministic actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import config
from core.actions import Actions

from .execution_context import ExecutionContext

DESKTOP_COMMAND_MATCHERS = (
    "_match_volume",
    "_match_scroll",
    "_match_tab",
    "_match_open_app",
    "_match_close_app",
    "_match_screenshot",
    "_match_media_control",
    "_match_window_management",
    "_match_folder_shortcut",
    "_match_quick_system",
)


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    action_status: str = "blocked"
    response: str = ""
    reason: Optional[str] = None
    pending_command: Optional[str] = None


class SafetyPolicy:
    @staticmethod
    def _is_desktop_command(query: str, actions: Actions) -> bool:
        return any(
            matcher and matcher(query)
            for matcher_name in DESKTOP_COMMAND_MATCHERS
            if (matcher := getattr(actions, matcher_name, None))
        )

    def evaluate(self, context: ExecutionContext, actions: Actions) -> SafetyDecision:
        if self._is_desktop_command(context.routing_text, actions):
            if not context.client_is_local:
                return SafetyDecision(
                    allowed=False,
                    response="Desktop control is available only from the local machine.",
                    reason="local_request_required",
                )
            if not getattr(config, "LOCAL_DESKTOP_MODE", False) or getattr(
                config, "WEB_SAFE_MODE", True
            ):
                return SafetyDecision(
                    allowed=False,
                    response=(
                        "Desktop control is disabled. Enable LOCAL_DESKTOP_MODE to use that command."
                    ),
                    reason="desktop_mode_disabled",
                )

        needs_confirmation = bool(actions._requires_confirmation(context.routing_text))
        if needs_confirmation and not context.confirm:
            return SafetyDecision(
                allowed=False,
                action_status="confirmation_required",
                response=(
                    "This action may delete data or change system settings. "
                    "Say yes to continue or no to cancel."
                ),
                reason="confirmation_required",
                pending_command=context.raw_text,
            )

        return SafetyDecision(allowed=True)
