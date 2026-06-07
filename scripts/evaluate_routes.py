#!/usr/bin/env python3
"""Evaluate deterministic command routing against labeled cases."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai.intent_evaluator import evaluate_cases, load_cases


def dataset_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(eval_cases_path: Path) -> dict:
    report = evaluate_cases(load_cases(eval_cases_path))
    per_intent = defaultdict(lambda: {"correct": 0, "total": 0})
    for result in report["results"]:
        intent = result["expected"]
        per_intent[intent]["total"] += 1
        per_intent[intent]["correct"] += int(result["passed"])

    report["dataset"] = eval_cases_path.name
    report["dataset_hash"] = dataset_hash(eval_cases_path)
    report["per_intent"] = {
        intent: {
            **counts,
            "accuracy": counts["correct"] / counts["total"],
        }
        for intent, counts in sorted(per_intent.items())
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-cases", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--min-accuracy", type=float, default=1.0)
    parser.add_argument("--min-intent-accuracy", type=float, default=0.0)
    args = parser.parse_args()

    report = build_report(args.eval_cases)
    print("Route evaluation summary:")
    print(json.dumps(report, indent=2))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report to {args.out}")

    if report["accuracy"] < args.min_accuracy:
        print(f"Accuracy too low: {report['accuracy']:.4f} < {args.min_accuracy:.4f}")
        return 2

    failed_intents = [
        (intent, metrics["accuracy"])
        for intent, metrics in report["per_intent"].items()
        if metrics["accuracy"] < args.min_intent_accuracy
    ]
    if failed_intents:
        print("The following intents failed the minimum intent accuracy check:")
        for intent, score in failed_intents:
            print(f"  - {intent}: {score:.4f} < {args.min_intent_accuracy:.4f}")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
