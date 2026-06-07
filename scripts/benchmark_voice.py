#!/usr/bin/env python3
"""Benchmark configured local STT/TTS providers without retaining audio."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.voice import LocalVoicePipeline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", type=Path, help="Optional 16 kHz mono PCM WAV for STT timing")
    parser.add_argument("--text", default="Meero local voice benchmark.")
    args = parser.parse_args()
    pipeline = LocalVoicePipeline()
    report = {"status": pipeline.status()}
    if args.wav:
        started = time.perf_counter()
        transcript = pipeline.transcribe(args.wav.read_bytes())
        report["stt"] = {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "transcript_chars": len(transcript),
        }
    started = time.perf_counter()
    audio = pipeline.synthesize(args.text)
    report["tts"] = {
        "latency_ms": (time.perf_counter() - started) * 1000,
        "audio_bytes": len(audio),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
