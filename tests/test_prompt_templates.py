from prompt_templates import build_external_payload, build_llama3_prompt


def test_llama3_prompt_includes_summary_and_recent_history_only():
    history = [(f"q{i}", f"a{i}") for i in range(7)]

    prompt = build_llama3_prompt("current question", history, memory_summary="older facts")

    assert "Long-term conversation summary: older facts" in prompt
    assert "q0" not in prompt
    assert "q1" not in prompt
    assert "q2" in prompt
    assert "current question" in prompt
    assert prompt.endswith("<|start_header_id|>assistant<|end_header_id|>\n")


def test_external_payload_keeps_structured_context():
    payload = build_external_payload("hello", [("q", "a")], memory_summary="summary")

    assert payload["input"] == "hello"
    assert payload["history"] == [("q", "a")]
    assert payload["memory_summary"] == "summary"
    assert "Meero" in payload["system"]
