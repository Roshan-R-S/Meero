import json

from backend import telemetry


def _write_event():
    telemetry.log_audit_event(
        command="private spoken command",
        action_status="success",
        response="private assistant response",
        engine="actions",
        sentiment="neutral",
        confidence=0.9,
        intent="test",
        latency_ms=12.5,
    )


def test_audit_log_omits_command_text_by_default(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(telemetry, "AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setattr(telemetry.config, "AUDIT_LOG_COMMAND_TEXT", False)

    _write_event()

    event = json.loads(audit_path.read_text(encoding="utf-8"))
    assert "command" not in event
    assert "response" not in event
    assert event["intent"] == "test"


def test_audit_log_includes_command_text_when_enabled(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(telemetry, "AUDIT_LOG_PATH", str(audit_path))
    monkeypatch.setattr(telemetry.config, "AUDIT_LOG_COMMAND_TEXT", True)

    _write_event()

    event = json.loads(audit_path.read_text(encoding="utf-8"))
    assert event["command"] == "private spoken command"
    assert event["response"] == "private assistant response"
