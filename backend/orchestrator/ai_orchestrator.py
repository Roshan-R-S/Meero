"""Main deterministic-first command orchestrator."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from backend.schemas import CommandOutcome
from backend.telemetry import log_audit_event
from core.actions import Actions
from core.mock_engine import MockSpeechEngine

from .decision_trace import DecisionTrace
from .execution_context import ExecutionContext
from .fallback_policy import FallbackPolicy
from .outcome_builder import OutcomeBuilder
from .safety_policy import SafetyPolicy

logger = logging.getLogger(__name__)


class AIOrchestrator:
    def __init__(
        self,
        *,
        safety_policy: Optional[SafetyPolicy] = None,
        fallback_policy: Optional[FallbackPolicy] = None,
        outcome_builder: Optional[OutcomeBuilder] = None,
    ):
        self.safety_policy = safety_policy or SafetyPolicy()
        self.fallback_policy = fallback_policy or FallbackPolicy()
        self.outcome_builder = outcome_builder or OutcomeBuilder()

    def execute(
        self,
        query: str,
        *,
        mode: str = "voice",
        confirm: bool = False,
        pending_command: Optional[str] = None,
        brain=None,
        llm=None,
        conversation_history=None,
        memory_summary_fn: Optional[Callable[[], str]] = None,
        append_conversation_fn: Optional[Callable[[str, str], None]] = None,
        analyze_sentiment_fn: Optional[Callable[[str], str]] = None,
        client_is_local: bool = True,
    ) -> CommandOutcome:
        started = time.perf_counter()
        context = ExecutionContext.build(
            query,
            mode=mode,
            confirm=confirm,
            pending_command=pending_command,
            client_is_local=client_is_local,
        )
        trace = DecisionTrace()
        metadata = {"engine": "actions"}
        outcome: Optional[CommandOutcome] = None

        try:
            engine = MockSpeechEngine()
            actions = Actions(engine)
            safety = self.safety_policy.evaluate(context, actions)
            if not safety.allowed:
                trace.add("safety", safety.action_status, reason=safety.reason)
                outcome = self.outcome_builder.build(
                    safety.response,
                    safety.action_status,
                    sentiment="negative" if safety.action_status == "blocked" else "neutral",
                    pending_command=safety.pending_command,
                    metadata={"engine": "actions", "fallback_reason": safety.reason},
                    trace=trace,
                )
                return outcome

            trace.add("safety", "allowed")
            result = actions.process_command(
                context.routing_text,
                input_func=(lambda: "yes") if context.confirm else (lambda: "None"),
                exit_func=lambda: engine.speak("Disconnecting..."),
            )
            if result == "neural_net_fallback":
                metadata = {"engine": "fallback", "fallback_reason": "actions_unhandled"}
                trace.add("actions", "unhandled", reason="actions_unhandled")
                summary = self._memory_summary(memory_summary_fn)
                response_text = self.fallback_policy.run(
                    routing_text=context.routing_text,
                    raw_text=context.raw_text,
                    brain=brain,
                    llm=llm,
                    history=conversation_history,
                    memory_summary=summary,
                    metadata=metadata,
                    trace=trace,
                )
                if not response_text:
                    response_text = "I am unable to process that request."
                    metadata.update(engine="none", fallback_reason="all_engines_failed")
                    trace.add("fallback", "failed", reason="all_engines_failed")
                engine.speak(response_text)
            else:
                trace.add("actions", "selected")

            final_response = engine.get_response() or "Done."
            self._append_conversation(append_conversation_fn, context.raw_text, final_response)
            sentiment = analyze_sentiment_fn(final_response) if analyze_sentiment_fn else "neutral"
            outcome = self.outcome_builder.build(
                final_response,
                "success",
                sentiment=sentiment,
                metadata=metadata,
                trace=trace,
            )
            return outcome
        except Exception as exc:
            logger.exception("Error executing command via orchestrator")
            trace.add("orchestrator", "failed", reason=type(exc).__name__)
            outcome = self.outcome_builder.build(
                "I encountered an internal error processing that command.",
                "error",
                sentiment="negative",
                metadata={"engine": "error", "fallback_reason": type(exc).__name__},
                trace=trace,
            )
            return outcome
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            if outcome is not None:
                outcome.metadata["latency_ms"] = latency_ms
                log_audit_event(
                    command=query,
                    action_status=outcome.action_status,
                    response=outcome.response,
                    engine=outcome.metadata.get("engine", "unknown"),
                    sentiment=outcome.sentiment,
                    confidence=outcome.metadata.get("confidence"),
                    intent=outcome.metadata.get("intent"),
                    latency_ms=latency_ms,
                )

    @staticmethod
    def _memory_summary(memory_summary_fn: Optional[Callable[[], str]]) -> str:
        if memory_summary_fn is None:
            return ""
        try:
            return memory_summary_fn()
        except Exception:
            logger.exception("Failed to read conversation summary")
            return ""

    @staticmethod
    def _append_conversation(append_fn, query: str, response: str) -> None:
        if append_fn is None:
            return
        try:
            append_fn(query, response)
        except Exception:
            logger.exception("Failed to write conversation to memory store")
