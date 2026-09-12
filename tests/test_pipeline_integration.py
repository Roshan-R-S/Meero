"""Tests for the 3-tier command pipeline: deterministic → neural → LLM fallback."""

import pytest
from unittest.mock import MagicMock, patch

from backend.orchestrator.ai_orchestrator import AIOrchestrator


def _make_mock_brain(label, confidence):
    brain = MagicMock()
    brain.predict.return_value = (label, confidence)
    return brain


def _make_mock_llm(response_text="I'm doing well, thank you!"):
    llm = MagicMock()
    llm.generate_response.return_value = response_text
    return llm


class TestThreeTierPipeline:
    """Parameterized end-to-end tests exercising all 3 routing tiers."""

    def test_tier1_deterministic_time(self):
        """Tier 1: 'what time is it' is handled entirely by actions.py."""
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            "what time is it",
            brain=None,
            llm=None,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.action_status == "success"
        assert "time is" in outcome.response.lower() or ":" in outcome.response

    def test_tier1_deterministic_greeting(self):
        """Tier 1: 'hello' is handled by the deterministic greeting matcher."""
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            "hello",
            brain=None,
            llm=None,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.action_status == "success"
        assert outcome.response  # Should have a greeting response

    def test_tier2_neural_net_high_confidence(self):
        """Tier 2: Brain recognizes with high confidence → neural net handles."""
        brain = _make_mock_brain("tell_joke", 0.95)
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            "tell me something funny",
            brain=brain,
            llm=None,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.action_status == "success"
        # Brain was consulted because the actions layer returned neural_net_fallback
        assert outcome.response

    def test_tier3_llm_fallback(self):
        """Tier 3: Unrecognized query falls through to LLM."""
        llm = _make_mock_llm("Here is what I think about quantum computing...")
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            "explain quantum entanglement in simple terms",
            brain=None,
            llm=llm,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.action_status == "success"
        assert "quantum" in outcome.response.lower() or outcome.metadata.get("engine") == "llm"

    def test_all_tiers_fail_gracefully(self):
        """When all 3 tiers fail, the orchestrator returns a safe fallback."""
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            "asdlkfjasldkfjaslkdfj completely nonsensical input",
            brain=None,
            llm=None,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.action_status in ("success", "error")
        assert outcome.response  # Should never be empty

    @pytest.mark.parametrize(
        "query,expected_engine",
        [
            ("what time is it", "actions"),
            ("hello meero", "actions"),
            ("good morning", "actions"),
        ],
    )
    def test_deterministic_commands_stay_in_tier1(self, query, expected_engine):
        """Verify that known deterministic commands never reach neural net or LLM."""
        brain = _make_mock_brain("irrelevant", 0.99)
        llm = _make_mock_llm()
        orchestrator = AIOrchestrator()
        outcome = orchestrator.execute(
            query,
            brain=brain,
            llm=llm,
            conversation_history=[],
            client_is_local=True,
        )
        assert outcome.metadata.get("engine") == expected_engine
        # Brain.predict and LLM.generate_response should NOT have been called
        brain.predict.assert_not_called()
        llm.generate_response.assert_not_called()
