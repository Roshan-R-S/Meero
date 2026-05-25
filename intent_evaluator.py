"""Small intent-evaluation helpers for CI regression tests."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from actions import Actions
from mock_engine import MockSpeechEngine


@dataclass(frozen=True)
class IntentCase:
    query: str
    expected_intent: str


def load_cases(path: str | Path) -> list[IntentCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [IntentCase(item["query"], item["expected_intent"]) for item in data["cases"]]


def classify_action_intent(query: str) -> str:
    """Classify command-router intent without executing the action handler."""
    actions = Actions(MockSpeechEngine())
    normalized = query.strip().lower()
    for matcher, handler in actions._commands:
        if matcher(normalized):
            if hasattr(handler, "__name__") and handler.__name__ != "<lambda>":
                return handler.__name__.replace("_handle_", "").replace("open_", "")
            name = getattr(matcher, "__name__", "")
            return name.replace("_match_", "")
    return "fallback"


def evaluate_cases(cases: list[IntentCase]) -> dict:
    results = []
    correct = 0
    for case in cases:
        actual = classify_action_intent(case.query)
        passed = actual == case.expected_intent
        correct += int(passed)
        results.append(
            {
                "query": case.query,
                "expected": case.expected_intent,
                "actual": actual,
                "passed": passed,
            }
        )
    total = len(cases)
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "results": results,
    }
