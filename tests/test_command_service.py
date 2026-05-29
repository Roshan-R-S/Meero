from backend.command_service import execute_command


class FakeLLM:
    def __init__(self):
        self.queries = []

    def generate_response(self, query, **_kwargs):
        self.queries.append(query)
        return "LLM response"


def test_desktop_command_blocked_when_desktop_mode_disabled(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", False)
    monkeypatch.setattr("config.WEB_SAFE_MODE", False)

    outcome = execute_command("open calculator")

    assert outcome.action_status == "blocked"
    assert outcome.metadata["fallback_reason"] == "desktop_mode_disabled"


def test_desktop_command_blocked_for_nonlocal_client(monkeypatch):
    monkeypatch.setattr("config.LOCAL_DESKTOP_MODE", True)
    monkeypatch.setattr("config.WEB_SAFE_MODE", False)

    outcome = execute_command("volume up", client_is_local=False)

    assert outcome.action_status == "blocked"
    assert outcome.metadata["fallback_reason"] == "local_request_required"


def test_raw_query_is_preserved_for_llm_and_memory(monkeypatch):
    monkeypatch.setattr("config.USE_NEURAL_NET", False)
    monkeypatch.setattr("config.USE_LLM", True)
    llm = FakeLLM()
    memory = []

    outcome = execute_command(
        "Who Is Roshan R S?",
        llm=llm,
        append_conversation_fn=lambda query, response: memory.append((query, response)),
    )

    assert outcome.action_status == "success"
    assert llm.queries == ["Who Is Roshan R S?"]
    assert memory[0][0] == "Who Is Roshan R S?"
