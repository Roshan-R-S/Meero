#!/usr/bin/env python3
"""Download, verify, and install a Vosk speech-recognition model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = PROJECT_ROOT / "models" / "vosk-model-small"
REQUIRED_DIRS = ("am", "conf", "graph")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(zip_path: Path, dest: Path) -> None:
    dest_resolved = dest.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (dest / member.filename).resolve()
            if target != dest_resolved and dest_resolved not in target.parents:
                raise RuntimeError(f"Unsafe archive member path: {member.filename}")
        archive.extractall(dest)


def find_model_root(extracted_dir: Path) -> Path:
    candidates = [extracted_dir]
    candidates.extend(path for path in extracted_dir.iterdir() if path.is_dir())
    for candidate in candidates:
        if all((candidate / name).is_dir() for name in REQUIRED_DIRS):
            return candidate
    raise RuntimeError("Extracted archive does not look like a Vosk model")


def verify_model_dir(model_dir: Path) -> None:
    missing = [name for name in REQUIRED_DIRS if not (model_dir / name).is_dir()]
    if missing:
        raise RuntimeError(f"Vosk model missing required directories: {', '.join(missing)}")
    if not (model_dir / "am" / "final.mdl").is_file():
        raise RuntimeError("Vosk model missing am/final.mdl")


def resolve_model_dir(path: Path) -> Path:
    try:
        verify_model_dir(path)
        return path
    except RuntimeError:
        if path.is_dir():
            for child in path.iterdir():
                if child.is_dir():
                    try:
                        verify_model_dir(child)
                        return child
                    except RuntimeError:
                        continue
        raise


def install_model(url: str, dest: Path, expected_sha256: str | None = None) -> Path:
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_name:
        temp_dir = Path(temp_name)
        zip_path = temp_dir / "model.zip"
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir()

        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, zip_path)

        actual_sha256 = sha256_file(zip_path)
        if expected_sha256 and actual_sha256.lower() != expected_sha256.lower():
            raise RuntimeError(
                "Checksum mismatch: "
                f"expected {expected_sha256.lower()}, got {actual_sha256.lower()}"
            )

        safe_extract(zip_path, extract_dir)
        extracted_model = find_model_root(extract_dir)
        verify_model_dir(extracted_model)

        staging = dest.with_name(f"{dest.name}.tmp")
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(extracted_model, staging)
        verify_model_dir(staging)

        if dest.exists():
            shutil.rmtree(dest)
        staging.replace(dest)

    manifest = {
        "url": url,
        "sha256": actual_sha256,
        "path": str(dest),
    }
    (dest / "download-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Vosk model installed at {dest}")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("VOSK_DOWNLOAD_URL", DEFAULT_URL))
    parser.add_argument("--dest", type=Path, default=Path(os.environ.get("VOSK_MODEL_PATH", DEFAULT_DEST)))
    parser.add_argument("--sha256", default=os.environ.get("VOSK_MODEL_SHA256"))
    parser.add_argument("--verify-only", action="store_true", help="Verify an existing model directory")
    args = parser.parse_args(argv)

    try:
        if args.verify_only:
            model_dir = resolve_model_dir(args.dest)
            print(f"Vosk model verified at {model_dir.resolve()}")
            return 0
        install_model(args.url, args.dest, args.sha256)
        return 0
    except Exception as exc:
        print(f"Vosk setup failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
