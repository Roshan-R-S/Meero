#!/usr/bin/env python3
"""Reproducible demo: runs a sample inference and validates key components.

This script is intentionally lightweight so it can be run in CI or locally.
"""
from __future__ import annotations

from pathlib import Path
import sys


def main():
    # Ensure model artifacts exist
    model_dir = Path("models")
    if not model_dir.exists():
        print("models/ not found — ensure you have run training or placed artifacts in models/")
        return 2

    # Run a quick dry-run publish validation (will require HF_TOKEN/HF_REPO env or will skip)
    import subprocess

    print("Running publish_artifacts.py --dry-run to validate HF credentials (if set)")
    subprocess.run([sys.executable, "scripts/publish_artifacts.py", "--artifact-dir", "models", "--dry-run"]) 

    # Run a simple inference benchmark (single iteration)
    print("Running a single inference to demonstrate model loading — see scripts/benchmark_inference.py for full benchmark")
    subprocess.run([sys.executable, "-c", "from ai.neural_net import NeuralNet; nn=NeuralNet(); print(nn.predict_with_confidence('hello'))"])

    print("Demo run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
