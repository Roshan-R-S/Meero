from core.prompt_templates import build_external_payload, build_llama3_prompt, clean_llm_response


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


def test_clean_llm_response_strips_prompt_artifacts():
    raw = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "You are Meero, Roshan's private AI assistant. <|eot_id|>"
        "<|start_header_id|>user<|end_header_id|>\n\nhello<|eot_id|>"
        "<|start_header_id|>assistant<|end_header_id|>\n\nHi there!"
    )

    assert clean_llm_response(raw) == "Hi there!"


def test_clean_llm_response_strips_history_and_reserved_tokens():
    raw = (
        "User: what is the meaning of life | Meero: The meaning of life is to find your purpose and make a difference in this world. "
        "User: tell me another joke | Meero: Why don't eggs tell jokes? They'd crack each other up! "
        "<|reserved_special_token_46|>"
    )

    assert clean_llm_response(raw) == "Why don't eggs tell jokes? They'd crack each other up!"
