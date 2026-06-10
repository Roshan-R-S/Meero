#!/usr/bin/env python3
"""Explicitly download and verify a local model asset."""

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
        urllib.request.urlretrieve(url, downloaded)
        actual = sha256_file(downloaded)
        if actual.lower() != expected_sha256.lower():
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--extract-zip", action="store_true")
    args = parser.parse_args(argv)
    try:
        download(args.url, args.dest, args.sha256, args.extract_zip)
        return 0
    except Exception as exc:
        print(f"Model setup failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
