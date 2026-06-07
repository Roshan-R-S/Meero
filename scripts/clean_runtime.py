#!/usr/bin/env python3
"""List or remove known generated/runtime files inside the repository."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ".pytest_cache",
    "build",
    "frontend/dist",
    "frontend/playwright-report",
    "frontend/test-results",
    "data/audit.jsonl",
    "data/conversation.db",
    "data/conversation.db-journal",
    "data/settings.json",
    "data/voice-cache",
    "data/screenshots",
    "models/main_eval.json",
    "models/unseen_eval.json",
    "models/voice_eval.json",
    "models/local_eval.json",
    "models/last_eval.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete targets; default is dry-run")
    args = parser.parse_args()
    for relative in TARGETS:
        target = (ROOT / relative).resolve()
        if target != ROOT and ROOT not in target.parents:
            raise RuntimeError(f"Refusing path outside repository: {target}")
        if not target.exists():
            continue
        print(("Removing" if args.apply else "Would remove") + f": {target}")
        if args.apply:
            shutil.rmtree(target) if target.is_dir() else target.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
