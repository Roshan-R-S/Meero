import os
import pytest


def test_model_evaluation_report_is_well_formed():
    # Skip if TensorFlow isn't available in the environment (keeps fast CI green)
    pytest.importorskip("tensorflow")

    from scripts import evaluate

    model_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "chat_model.h5")
    tokenizer_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "tokenizer.pkl")
    label_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "label_encoder.pkl")
    intents_path = os.path.join(os.path.dirname(__file__), os.pardir, "data", "intents.json")
    model_path = os.path.normpath(model_path)
    tokenizer_path = os.path.normpath(tokenizer_path)
    label_path = os.path.normpath(label_path)
    intents_path = os.path.normpath(intents_path)

    missing_artifacts = [
        path
        for path in (model_path, tokenizer_path, label_path)
        if not os.path.exists(path)
    ]
    if missing_artifacts:
        pytest.skip(
            "Generated model artifacts are not available: "
            + ", ".join(os.path.basename(path) for path in missing_artifacts)
        )

    report = evaluate.evaluate(model_path, tokenizer_path, label_path, intents_path)
    assert report["samples"] > 0
    assert 0.0 <= report["accuracy"] <= 1.0
    assert report["dataset"] == "intents.json"
    assert "classification_report" in report
    assert "accuracy" in report["classification_report"]
