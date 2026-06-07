from pathlib import Path

from scripts.evaluate_routes import build_report


def test_voice_route_evaluation_report_is_perfect():
    report = build_report(Path("data/voice_eval_cases.json"))

    assert report["accuracy"] == 1.0
    assert report["dataset"] == "voice_eval_cases.json"
    assert all(metrics["accuracy"] == 1.0 for metrics in report["per_intent"].values())
