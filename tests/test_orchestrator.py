import json

from backend.command_service import execute_command
from backend.orchestrator.execution_context import ExecutionContext


class FakeLLM:
    def __init__(self):
        self.queries = []

    def generate_response(self, query, **_kwargs):
        self.queries.append(query)
        return "Local response"


def test_execution_context_preserves_raw_text_and_normalizes_only_routing_text():
    context = ExecutionContext.build("Hey Miro Launch Visual Studio Coat")

    assert context.raw_text == "Hey Miro Launch Visual Studio Coat"
    assert context.routing_text == "launch visual studio code"


def test_decision_trace_contains_no_user_text(monkeypatch):
    monkeypatch.setattr("config.USE_NEURAL_NET", False)
    monkeypatch.setattr("config.USE_LLM", True)
    llm = FakeLLM()
    raw_text = "Private User Phrase With Unique Words"

    outcome = execute_command(raw_text, llm=llm)

    assert llm.queries == [raw_text]
    assert raw_text not in json.dumps(outcome.metadata)
    assert outcome.metadata["decision_trace"]


def test_orchestrator_applies_asr_corrections_before_desktop_safety(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", False)
    monkeypatch.setattr("config.WEB_SAFE_MODE", False)

    outcome = execute_command("hey miro launch cal cue later")

    assert outcome.action_status == "blocked"
    assert outcome.metadata["fallback_reason"] == "desktop_mode_disabled"
