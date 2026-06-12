"""Neural then local-LLM fallback policy."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import config
from core.prompt_templates import clean_llm_response

from .decision_trace import DecisionTrace

logger = logging.getLogger(__name__)

NEURAL_FAILURE_PHRASES = {
    "I'm afraid I didn't catch that, sir.",
    "Could you rephrase that directive?",
    "My processing units require clarification, sir.",
    "I'm not sure how to respond to that.",
}


class FallbackPolicy:
    def run(
        self,
        *,
        routing_text: str,
        raw_text: str,
        brain,
        llm,
        history,
        memory_summary: str,
        metadata: dict[str, Any],
        trace: DecisionTrace,
    ) -> Optional[str]:
        response_text = self._run_neural(routing_text, brain, metadata, trace)
        if response_text:
            return response_text
        return self._run_llm(raw_text, llm, history, memory_summary, metadata, trace)

    @staticmethod
    def _run_neural(query, brain, metadata, trace) -> Optional[str]:
        started = time.perf_counter()
        if not getattr(config, "USE_NEURAL_NET", True):
            metadata["fallback_reason"] = "neural_net_disabled"
            trace.add(
                "neural_net",
                "skipped",
                reason="disabled",
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
            return None
        if not brain:
            metadata["fallback_reason"] = "neural_net_unavailable"
            trace.add(
                "neural_net",
                "skipped",
                reason="unavailable",
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
            return None

        try:
            if hasattr(brain, "predict_with_confidence"):
                response, confidence, intent = brain.predict_with_confidence(query)
            else:
                response = brain.predict(query)
                confidence, intent = (1.0 if response else 0.0), None
        except Exception:
            logger.exception("Error during neural net prediction")
            response, confidence, intent = None, 0.0, None

        metadata["confidence"] = round(confidence, 4)
        if intent:
            metadata["intent"] = intent
        threshold = getattr(config, "NEURAL_NET_CONFIDENCE_THRESHOLD", 0.8)
        if response and response not in NEURAL_FAILURE_PHRASES and confidence >= threshold:
            metadata.update(engine="neural_net", fallback_reason=None)
            trace.add(
                "neural_net",
                "selected",
                confidence=confidence,
                intent=intent,
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
            return response

        reason = "neural_net_noanswer" if response in NEURAL_FAILURE_PHRASES else "neural_net_low_confidence"
        metadata["fallback_reason"] = reason
        trace.add(
            "neural_net",
            "rejected",
            reason=reason,
            confidence=confidence,
            intent=intent,
            latency_ms=FallbackPolicy._elapsed_ms(started),
        )
        return None

    @staticmethod
    def _run_llm(raw_text, llm, history, memory_summary, metadata, trace) -> Optional[str]:
        started = time.perf_counter()
        if not getattr(config, "USE_LLM", True):
            metadata["fallback_reason"] = "llm_disabled"
            trace.add(
                "local_llm",
                "skipped",
                reason="disabled",
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
            return None
        if not llm:
            metadata["fallback_reason"] = "local_llm_unavailable"
            trace.add(
                "local_llm",
                "skipped",
                reason="unavailable",
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
            return None

        try:
            response = clean_llm_response(
                llm.generate_response(raw_text, history=history, memory_summary=memory_summary)
            )
            if response:
                metadata["engine"] = "local_llm"
                trace.add(
                    "local_llm",
                    "selected",
                    latency_ms=FallbackPolicy._elapsed_ms(started),
                )
                return response
        except Exception:
            logger.exception("Local LLM generation failed")
            metadata["fallback_reason"] = "local_llm_error"
            trace.add(
                "local_llm",
                "failed",
                reason="local_llm_error",
                latency_ms=FallbackPolicy._elapsed_ms(started),
            )
        return None

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1000
