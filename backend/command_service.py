import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ai.external_llm import ExternalLLM
from core.actions import Actions
from core.mock_engine import MockSpeechEngine
from core.prompt_templates import clean_llm_response

import config

logger = logging.getLogger(__name__)

NEURAL_FAILURE_PHRASES = {
    "I'm afraid I didn't catch that, sir.",
    "Could you rephrase that directive?",
    "My processing units require clarification, sir.",
    "I'm not sure how to respond to that.",
}


DESKTOP_COMMAND_MATCHERS = (
    "_match_volume",
    "_match_scroll",
    "_match_tab",
    "_match_open_app",
    "_match_close_app",
    "_match_screenshot",
)


@dataclass
class CommandOutcome:
    response: str
    action_status: str
    sentiment: str = "neutral"
    pending_command: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _memory_summary(memory_summary_fn: Optional[Callable[[], str]]) -> str:
    if memory_summary_fn is None:
        return ""

    try:
        return memory_summary_fn()
    except Exception:
        logger.exception("Failed to read conversation summary")
        return ""


def _append_conversation(
    append_conversation_fn: Optional[Callable[[str, str], None]],
    query: str,
    response: str,
) -> None:
    if append_conversation_fn is None:
        return

    try:
        append_conversation_fn(query, response)
    except Exception:
        logger.exception("Failed to write conversation to memory store")


def _run_neural_fallback(query: str, brain, metadata: dict[str, Any]) -> tuple[Optional[str], dict[str, Any]]:
    response_text = None

    if getattr(config, "USE_NEURAL_NET", True) and brain:
        try:
            if hasattr(brain, "predict_with_confidence"):
                response_text, confidence = brain.predict_with_confidence(query)
            else:
                response_text = brain.predict(query)
                confidence = 1.0 if response_text else 0.0
        except Exception:
            logger.exception("Error during neural net prediction")
            response_text, confidence = None, 0.0

        metadata["confidence"] = round(confidence, 4)
        threshold = getattr(config, "NEURAL_NET_CONFIDENCE_THRESHOLD", 0.8)
        if response_text and response_text not in NEURAL_FAILURE_PHRASES and confidence >= threshold:
            metadata["engine"] = "neural_net"
            metadata["fallback_reason"] = None
        elif response_text in NEURAL_FAILURE_PHRASES:
            response_text = None
            metadata["fallback_reason"] = "neural_net_noanswer"
        else:
            response_text = None
            metadata["fallback_reason"] = "neural_net_low_confidence"
    elif not getattr(config, "USE_NEURAL_NET", True):
        metadata["fallback_reason"] = "neural_net_disabled"
    else:
        metadata["fallback_reason"] = "neural_net_unavailable"

    return response_text, metadata


def _run_llm_fallback(
    query: str,
    llm,
    external_llm: Optional[ExternalLLM],
    history,
    summary: str,
    metadata: dict[str, Any],
) -> tuple[Optional[str], dict[str, Any]]:
    response_text = None

    if getattr(config, "USE_LLM", True):
        if llm:
            try:
                response_text = llm.generate_response(
                    query,
                    history=history,
                    memory_summary=summary,
                )
                response_text = clean_llm_response(response_text)
                if response_text:
                    metadata["engine"] = "local_llm"
            except Exception:
                logger.exception("Local LLM generation failed")
                metadata["fallback_reason"] = "local_llm_error"
        else:
            metadata["fallback_reason"] = "local_llm_unavailable"

        if not response_text and external_llm:
            try:
                response_text = external_llm.generate_response(
                    query,
                    history=history,
                    memory_summary=summary,
                )
                response_text = clean_llm_response(response_text)
                if response_text:
                    metadata["engine"] = "external_llm"
            except Exception:
                logger.exception("External LLM generation failed")
                metadata["fallback_reason"] = "external_llm_error"
        elif not response_text and external_llm is None:
            metadata["fallback_reason"] = "external_llm_unavailable"
    elif not response_text:
        metadata["fallback_reason"] = "llm_disabled"

    return response_text, metadata


def _is_desktop_command(query: str, actions: Actions) -> bool:
    for matcher_name in DESKTOP_COMMAND_MATCHERS:
        matcher = getattr(actions, matcher_name, None)
        if matcher and matcher(query):
            return True
    return False


def execute_command(
    query: str,
    *,
    confirm: bool = False,
    pending_command: Optional[str] = None,
    brain=None,
    llm=None,
    external_llm: Optional[ExternalLLM] = None,
    conversation_history=None,
    memory_summary_fn: Optional[Callable[[], str]] = None,
    append_conversation_fn: Optional[Callable[[str, str], None]] = None,
    analyze_sentiment_fn: Optional[Callable[[str], str]] = None,
    client_is_local: bool = True,
) -> CommandOutcome:
    raw_query = (pending_command or query).strip()
    normalized_query = raw_query.lower()
    mock_engine = MockSpeechEngine()
    actions = Actions(mock_engine)
    metadata: dict[str, Any] = {"engine": "actions"}

    def dummy_input():
        return "None"

    def dummy_exit():
        mock_engine.speak("Disconnecting...")

    try:
        if _is_desktop_command(normalized_query, actions):
            if not client_is_local:
                return CommandOutcome(
                    response="Desktop control is available only from the local machine.",
                    action_status="blocked",
                    sentiment="negative",
                    metadata={
                        "engine": "actions",
                        "fallback_reason": "local_request_required",
                    },
                )
            if not getattr(config, "LOCAL_DESKTOP_MODE", True) or getattr(config, "WEB_SAFE_MODE", False):
                return CommandOutcome(
                    response="Desktop control is disabled. Enable LOCAL_DESKTOP_MODE to use that command.",
                    action_status="blocked",
                    sentiment="neutral",
                    metadata={
                        "engine": "actions",
                        "fallback_reason": "desktop_mode_disabled",
                    },
                )

        needs_confirmation = bool(
            hasattr(actions, "_requires_confirmation") and actions._requires_confirmation(normalized_query)
        )
        if needs_confirmation and not confirm:
            return CommandOutcome(
                response=(
                    "This action may delete data or change system settings. "
                    "Say yes to continue or no to cancel."
                ),
                action_status="confirmation_required",
                sentiment="neutral",
                pending_command=raw_query,
                metadata={
                    "engine": "actions",
                    "fallback_reason": "confirmation_required",
                },
            )

        confirmation_input = (lambda: "yes") if confirm else dummy_input
        result = actions.process_command(
            normalized_query,
            input_func=confirmation_input,
            exit_func=dummy_exit,
        )

        if result == "neural_net_fallback":
            metadata = {"engine": "fallback", "fallback_reason": "actions_unhandled"}
            response_text = None

            response_text, metadata = _run_neural_fallback(normalized_query, brain, metadata)

            if not response_text and getattr(config, "USE_LLM", True):
                summary = _memory_summary(memory_summary_fn)
                response_text, metadata = _run_llm_fallback(
                    raw_query,
                    llm,
                    external_llm,
                    conversation_history,
                    summary,
                    metadata,
                )

            if not response_text:
                response_text = "I am unable to process that request."
                metadata["engine"] = "none"
                metadata["fallback_reason"] = metadata.get("fallback_reason") or "all_engines_failed"

            mock_engine.speak(response_text)

        final_response = mock_engine.get_response() or "Done."

        _append_conversation(append_conversation_fn, raw_query, final_response)

        sentiment = analyze_sentiment_fn(final_response) if analyze_sentiment_fn else "neutral"
        return CommandOutcome(
            response=final_response,
            action_status="success",
            sentiment=sentiment,
            pending_command=None,
            metadata=metadata,
        )
    except Exception as exc:
        logger.exception("Error processing command")
        return CommandOutcome(
            response="I encountered an internal error. Please try again.",
            action_status="error",
            sentiment="negative",
            metadata={"engine": "error", "fallback_reason": type(exc).__name__},
        )
