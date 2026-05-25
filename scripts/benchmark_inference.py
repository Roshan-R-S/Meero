#!/usr/bin/env python3
"""Simple inference benchmark for the neural net model.

Runs a small set of sample inputs through `neural_net.NeuralNet.predict_with_confidence`
and reports timings and basic statistics.
"""
from __future__ import annotations

import time
import statistics
from pathlib import Path

import config


def load_model():
    from neural_net import NeuralNet

    nn = NeuralNet()
    return nn


def main():
    samples = [
        "what is the time",
        "open notepad",
        "set volume to 50 percent",
        "tell me a joke",
        "what's the weather today",
    ]
    nn = load_model()
    latencies = []
    for i in range(10):
        for s in samples:
            start = time.perf_counter()
            resp, conf = nn.predict_with_confidence(s)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
            print(f"Sample: {s!r} -> conf={conf:.3f} resp={resp[:60]!r} time={latencies[-1]:.1f}ms")

    times = [t for t in latencies]
    print("\nLatency stats (ms):")
    print(f"  count: {len(times)}")
    print(f"  mean: {statistics.mean(times):.2f}")
    print(f"  median: {statistics.median(times):.2f}")
    print(f"  p95: {statistics.quantiles(times, n=100)[94]:.2f}")


if __name__ == "__main__":
    main()
