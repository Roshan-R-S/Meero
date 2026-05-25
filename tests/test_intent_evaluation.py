from pathlib import Path

from intent_evaluator import evaluate_cases, load_cases


def test_intent_validation_set_routes_expected_commands():
    cases = load_cases(Path("tests/fixtures/intent_validation.json"))

    report = evaluate_cases(cases)

    assert report["accuracy"] == 1.0, report["results"]
