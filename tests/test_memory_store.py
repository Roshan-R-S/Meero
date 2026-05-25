import memory_store


def test_append_prunes_old_turns_into_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(memory_store, "DB_PATH", str(tmp_path / "conversation.db"))

    for index in range(5):
        memory_store.append(f"q{index}", f"a{index}", max_interactions=3)

    assert memory_store.last(10) == [("q2", "a2"), ("q3", "a3"), ("q4", "a4")]
    summary = memory_store.get_summary()
    assert "q0" in summary
    assert "q1" in summary
    assert "q4" not in summary


def test_summarize_turns_caps_summary_length():
    summary = memory_store.summarize_turns(
        [("question", "answer")],
        existing_summary="x" * 100,
        max_chars=40,
    )

    assert len(summary) <= 40
    assert "answer" in summary
