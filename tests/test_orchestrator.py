import json
import subprocess

from backend.command_service import execute_command
from backend.orchestrator.ai_orchestrator import AIOrchestrator
from backend.orchestrator.decision_trace import DecisionTrace
from backend.orchestrator.execution_context import ExecutionContext
from core.actions import Actions
from core.mock_engine import MockSpeechEngine
from core.response_collector import ResponseCollector


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


def test_orchestrator_factories_create_fresh_command_dependencies():
    collectors = []
    actions_instances = []

    def collector_factory():
        collector = ResponseCollector()
        collectors.append(collector)
        return collector

    def actions_factory(collector):
        actions = Actions(collector)
        actions_instances.append(actions)
        return actions

    orchestrator = AIOrchestrator(
        response_collector_factory=collector_factory,
        actions_factory=actions_factory,
    )

    first = orchestrator.execute("what time is it")
    second = orchestrator.execute("what time is it")

    assert first.action_status == "success"
    assert second.action_status == "success"
    assert len(collectors) == 2
    assert len(actions_instances) == 2
    assert collectors[0] is not collectors[1]
    assert actions_instances[0] is not actions_instances[1]


def test_mock_speech_engine_remains_a_compatibility_alias():
    assert MockSpeechEngine is ResponseCollector


def test_decision_trace_accepts_provider_without_accepting_private_text():
    trace = DecisionTrace()
    trace.add("stt", "selected", provider="vosk", transcript="private words")

    assert trace.to_list() == [{"stage": "stt", "status": "selected", "provider": "vosk"}]


def test_orchestrator_trace_covers_deterministic_and_failed_fallback(monkeypatch):
    deterministic = AIOrchestrator().execute("what time is it")
    assert [step["stage"] for step in deterministic.metadata["decision_trace"]] == [
        "safety",
        "actions",
    ]

    monkeypatch.setattr("config.USE_NEURAL_NET", False)
    monkeypatch.setattr("config.USE_LLM", False)
    failed = AIOrchestrator().execute("unhandled private phrase")
    assert failed.metadata["fallback_reason"] == "all_engines_failed"
    assert failed.metadata["decision_trace"][-1] == {
        "stage": "fallback",
        "status": "failed",
        "reason": "all_engines_failed",
    }


def test_orchestrator_factory_failure_returns_safe_error():
    def broken_factory(_collector):
        raise RuntimeError("private factory failure")

    outcome = AIOrchestrator(actions_factory=broken_factory).execute("hello")

    assert outcome.action_status == "error"
    assert outcome.response == "I encountered an internal error processing that command."
    assert "private factory failure" not in json.dumps(outcome.metadata)


def test_desktop_subprocess_timeout_returns_safe_error_trace(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.WEB_SAFE_MODE", False)
    monkeypatch.setattr("config.APP_CLOSE_ALLOWLIST", ("private-app",))
    monkeypatch.setattr(
        "app_launcher.subprocess.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("taskkill", 5)),
    )

    outcome = AIOrchestrator().execute("close private-app", confirm=True)

    assert outcome.action_status == "error"
    assert outcome.response.endswith("Closing the application timed out.")
    assert "private-app" not in outcome.response
    assert outcome.metadata["fallback_reason"] == "desktop_subprocess_timeout"
    assert outcome.metadata["decision_trace"][-1] == {
        "stage": "actions",
        "status": "failed",
        "reason": "desktop_subprocess_timeout",
    }
    assert "private-app" not in json.dumps(outcome.metadata)
