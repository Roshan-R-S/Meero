#!/usr/bin/env python3
"""Evaluate a saved intent classification model.

Outputs accuracy, average latency, confidence stats, and writes a JSON report.
"""
import argparse
import json
import time
import os
import statistics
import pickle
import hashlib

import numpy as np

from sklearn.metrics import classification_report
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Ensure project root is on sys.path so we can import config when executed from scripts/
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config
from ai.keras_compat import load_model_compat


def compute_dataset_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_dataset(intents_path):
    with open(intents_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = []
    labels = []
    for intent in data.get("intents", []):
        tag = intent.get("tag")
        for pattern in intent.get("patterns", []):
            texts.append(pattern)
            labels.append(tag)
    return texts, labels


def evaluate(model_path, tokenizer_path, label_encoder_path, intents_path, maxlen=None, threshold=0.4, sample_latency_n=100):
    model = load_model_compat(model_path)

    with open(tokenizer_path, "rb") as f:
        tokenizer = pickle.load(f)
    with open(label_encoder_path, "rb") as f:
        label_encoder = pickle.load(f)

    texts, labels = load_dataset(intents_path)
    if not texts:
        raise RuntimeError("No evaluation data found in intents file")

    maxlen = maxlen or getattr(config, "NEURAL_NET_MAXLEN", 20)
    sequences = tokenizer.texts_to_sequences(texts)
    X = pad_sequences(sequences, maxlen=maxlen, truncating='post')

    # Model predictions (batch)
    probs = model.predict(X, verbose=0)
    top_probs = probs.max(axis=1)
    preds_idx = probs.argmax(axis=1)
    preds = label_encoder.inverse_transform(preds_idx)

    # Accuracy
    correct = sum(1 for p, t in zip(preds, labels) if p == t)
    accuracy = correct / len(labels)

    # Hallucination-like metric: low-confidence predictions
    low_conf_count = sum(1 for p in top_probs if p < threshold)
    hallucination_rate = low_conf_count / len(top_probs)

    # Latency: measure single-sample prediction latency on up to sample_latency_n samples
    latencies = []
    n = min(sample_latency_n, len(X))
    for i in range(n):
        x = np.expand_dims(X[i], 0)
        t0 = time.perf_counter()
        _ = model.predict(x, verbose=0)
        t1 = time.perf_counter()
        latencies.append(t1 - t0)

    report = {
        "model": os.path.basename(model_path),
        "tokenizer": os.path.basename(tokenizer_path),
        "label_encoder": os.path.basename(label_encoder_path),
        "dataset": os.path.basename(intents_path),
        "dataset_hash": compute_dataset_hash(intents_path),
        "samples": len(labels),
        "accuracy": accuracy,
        "hallucination_rate": hallucination_rate,
        "confidence_mean": float(top_probs.mean()),
        "confidence_median": float(statistics.median(top_probs)),
        "latency_mean_s": float(statistics.mean(latencies)) if latencies else None,
        "latency_median_s": float(statistics.median(latencies)) if latencies else None,
        "classification_report": classification_report(
            labels,
            preds,
            output_dict=True,
            zero_division=0,
        ),
    }

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="models/chat_model.h5")
    parser.add_argument("--tokenizer", type=str, default="models/tokenizer.pkl")
    parser.add_argument("--label-encoder", type=str, default="models/label_encoder.pkl")
    parser.add_argument("--intents", type=str, default="intents.json")
    parser.add_argument("--maxlen", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.4)
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=float(os.environ.get("MODEL_MIN_ACCURACY", "0.85")),
        help="Fail with exit code 2 when accuracy is below this value",
    )
    parser.add_argument("--latency-samples", type=int, default=100)
    parser.add_argument("--out", type=str, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    report = evaluate(args.model, args.tokenizer, args.label_encoder, args.intents, maxlen=args.maxlen, threshold=args.threshold, sample_latency_n=args.latency_samples)

    print("Evaluation summary:")
    print(json.dumps(report, indent=2))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Wrote report to {args.out}")

    if report["accuracy"] < args.min_accuracy:
        print(f"Accuracy too low: {report['accuracy']:.4f} < {args.min_accuracy:.4f}")
        sys.exit(2)


if __name__ == '__main__':
    main()
