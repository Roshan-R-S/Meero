from pathlib import Path

from ai.intent_evaluator import evaluate_cases, load_cases


def test_intent_validation_set_routes_expected_commands():
    cases = load_cases(Path("tests/fixtures/intent_validation.json"))

    report = evaluate_cases(cases)

    assert report["accuracy"] == 1.0, report["results"]


def test_unseen_intent_eval_cases_route_expected_commands():
    cases = load_cases(Path("data/intent_eval_cases.json"))

    report = evaluate_cases(cases)

    # The baseline neural net model evaluates at around 53% on the 30 unseen diverse cases.
    assert report["accuracy"] >= 0.5, report["results"]
