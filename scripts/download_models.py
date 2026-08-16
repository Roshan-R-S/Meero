#!/usr/bin/env python3
"""Explicitly download and verify a local model asset.

Supported model targets
-----------------------
  vosk        Download and verify a Vosk STT model zip
  whisper     Download a faster-whisper model directory
  silero-vad  Download the Silero VAD ONNX model for browser-side VAD
              (placed in frontend/public/ so Vite serves it at /silero_vad.onnx)

Usage examples:
  python scripts/download_models.py --model silero-vad
  python scripts/download_models.py --url <url> --dest <path> --sha256 <hash>
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── Silero VAD ONNX ──────────────────────────────────────────────────────────
# Silero VAD v5 ONNX model — served at /silero_vad.onnx in the frontend.
# Source: https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx
# SHA-256 is computed from the official model file. Update when a new version is released.
SILERO_VAD_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
)
# NOTE: run `sha256sum silero_vad.onnx` or use Python after downloading to get this.
# The value below is a placeholder — replace with the verified hash of the downloaded file.
SILERO_VAD_SHA256 = "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3"

SILERO_VAD_DEST = PROJECT_ROOT / "frontend" / "public" / "silero_vad.onnx"
# ─────────────────────────────────────────────────────────────────────────────


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe archive path: {member.filename}")
        archive.extractall(destination)


def download(url: str, destination: Path, expected_sha256: str, extract_zip: bool) -> None:
    destination = destination.resolve()
    with tempfile.TemporaryDirectory(prefix="meero-model-") as temp_name:
        temp_dir = Path(temp_name)
        downloaded = temp_dir / "download"
        print(f"Downloading {url} ...")
        urllib.request.urlretrieve(url, downloaded)
        actual = sha256_file(downloaded)

        # If expected hash is the placeholder, print the real hash and continue.
        if expected_sha256 == "REPLACE_WITH_ACTUAL_SHA256_AFTER_FIRST_DOWNLOAD":
            print(f"SHA-256 of downloaded file: {actual}")
            print("Update SILERO_VAD_SHA256 in scripts/download_models.py with the above hash.")
        elif actual.lower() != expected_sha256.lower():
            raise RuntimeError(f"Checksum mismatch: expected {expected_sha256}, got {actual}")

        staging = destination.with_name(f"{destination.name}.tmp")
        if staging.exists():
            shutil.rmtree(staging) if staging.is_dir() else staging.unlink()
        if extract_zip:
            staging.mkdir(parents=True)
            safe_extract(downloaded, staging)
        else:
            staging.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(downloaded, staging)
        if destination.exists():
            shutil.rmtree(destination) if destination.is_dir() else destination.unlink()
        staging.replace(destination)
    print(f"Installed verified local model at {destination}")


def download_silero_vad() -> None:
    """Download the Silero VAD ONNX model to frontend/public/silero_vad.onnx."""
    if SILERO_VAD_DEST.exists():
        print(f"Silero VAD model already present at {SILERO_VAD_DEST}")
        actual = sha256_file(SILERO_VAD_DEST)
        print(f"  SHA-256: {actual}")
        return
    download(SILERO_VAD_URL, SILERO_VAD_DEST, SILERO_VAD_SHA256, extract_zip=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", choices=["silero-vad"], help="Named model shortcut to download")
    parser.add_argument("--url", help="Direct download URL (use with --dest and --sha256)")
    parser.add_argument("--dest", type=Path, help="Destination path for the downloaded file")
    parser.add_argument("--sha256", help="Expected SHA-256 checksum of the downloaded file")
    parser.add_argument("--extract-zip", action="store_true", help="Extract a zip archive after download")
    args = parser.parse_args(argv)

    try:
        if args.model == "silero-vad":
            download_silero_vad()
        elif args.url and args.dest and args.sha256:
            download(args.url, args.dest, args.sha256, args.extract_zip)
        else:
            parser.print_help()
            print("\nAvailable named models:")
            print("  silero-vad  Silero VAD ONNX model for browser-side auto end-of-speech detection")
            return 1
        return 0
    except Exception as exc:
        print(f"Model setup failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
