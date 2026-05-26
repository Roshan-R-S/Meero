import json
import os
import pytest


def test_model_accuracy_against_baseline():
    # Skip if TensorFlow isn't available in the environment (keeps fast CI green)
    tf = pytest.importorskip("tensorflow")

    from scripts import evaluate

    model_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "chat_model.h5")
    tokenizer_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "tokenizer.pkl")
    label_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "label_encoder.pkl")
    intents_path = os.path.join(os.path.dirname(__file__), os.pardir, "intents.json")
    model_path = os.path.normpath(model_path)
    tokenizer_path = os.path.normpath(tokenizer_path)
    label_path = os.path.normpath(label_path)
    intents_path = os.path.normpath(intents_path)

    baseline_path = os.path.join(os.path.dirname(__file__), os.pardir, "models", "baseline_eval.json")
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    report = evaluate.evaluate(model_path, tokenizer_path, label_path, intents_path)
    assert report["accuracy"] >= baseline.get("accuracy", 0.0), f"Model accuracy {report['accuracy']} below baseline {baseline.get('accuracy')}"
