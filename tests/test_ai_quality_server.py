from fastapi.testclient import TestClient


class FakeBrain:
    def __init__(self, response, confidence):
        self.response = response
        self.confidence = confidence

    def predict_with_confidence(self, query):
        return self.response, self.confidence


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_response(self, query, history=None, memory_summary=None):
        self.calls.append(
            {
                "query": query,
                "history": list(history or []),
                "memory_summary": memory_summary,
            }
        )
        return self.response


def client_with_server_state(monkeypatch, brain=None, llm=None, external_llm=None, summary=""):
    import backend.app as server

    server.LAST_COMMAND_TIME = 0
    server.CONVERSATION_HISTORY.clear()
    server.CONVERSATION_HISTORY.extend([("previous question", "previous answer")])
    monkeypatch.setattr(server, "brain", brain)
    monkeypatch.setattr(server, "llm", llm)
    monkeypatch.setattr(server, "external_llm", external_llm)
    monkeypatch.setattr(server, "_memory_summary", lambda: summary)
    monkeypatch.setattr(server.memory_store, "append", lambda *args, **kwargs: None)
    return TestClient(server.app)


def test_command_response_tracks_neural_net_confidence(monkeypatch):
    client = client_with_server_state(monkeypatch, brain=FakeBrain("Neural answer", 0.93))

    response = client.post("/command", json={"command": "explain my project status"})

    data = response.json()
    assert data["response"] == "Neural answer"
    assert data["metadata"]["engine"] == "neural_net"
    assert data["metadata"]["confidence"] == 0.93
    assert data["metadata"]["fallback_reason"] is None


def test_low_confidence_neural_net_falls_back_to_local_llm_with_summary(monkeypatch):
    fake_llm = FakeLLM("LLM answer")
    client = client_with_server_state(
        monkeypatch,
        brain=FakeBrain("Maybe", 0.2),
        llm=fake_llm,
        summary="older memory summary",
    )

    response = client.post("/command", json={"command": "explain my project status"})

    data = response.json()
    assert data["response"] == "LLM answer"
    assert data["metadata"]["engine"] == "local_llm"
    assert data["metadata"]["confidence"] == 0.2
    assert data["metadata"]["fallback_reason"] == "neural_net_low_confidence"
    assert fake_llm.calls[0]["memory_summary"] == "older memory summary"
    assert fake_llm.calls[0]["history"] == [("previous question", "previous answer")]


def test_llm_prompt_echo_is_cleaned_before_response(monkeypatch):
    raw_llm_output = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "You are Meero, Roshan's private AI assistant. <|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\nhello<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\nClean reply"
    )
    fake_llm = FakeLLM(raw_llm_output)
    client = client_with_server_state(
        monkeypatch,
        brain=FakeBrain("Maybe", 0.2),
        llm=fake_llm,
    )

    response = client.post("/command", json={"command": "what is the meaning of life"})

    data = response.json()
    assert data["response"] == "Clean reply"
    assert data["metadata"]["engine"] == "local_llm"


def test_greeting_is_handled_by_actions_without_llm(monkeypatch):
    fake_brain = FakeBrain(None, 0.0)
    fake_llm = FakeLLM("Should not be used")
    client = client_with_server_state(
        monkeypatch,
        brain=fake_brain,
        llm=fake_llm,
    )

    response = client.post("/command", json={"command": "hi"})

    data = response.json()
    assert data["response"] == "I'm here to help. What can I assist you with today?"
    assert data["metadata"]["engine"] == "actions"
    assert fake_llm.calls == []


def test_response_tracks_action_engine_for_direct_commands(monkeypatch):
    client = client_with_server_state(monkeypatch)

    response = client.post("/command", json={"command": "what time is it"})

    data = response.json()
    assert data["action_status"] == "success"
    assert data["metadata"]["engine"] == "actions"
