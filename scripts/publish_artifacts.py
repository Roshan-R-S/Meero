#!/usr/bin/env python3
"""Publish a prepared artifact directory to Hugging Face Hub.

Provides a small CLI wrapper around `huggingface_hub` with optional
dry-run, manifest validation and simple retry logic for transient failures.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional


def _validate_manifest(artifact_dir: Path) -> bool:
    manifest = artifact_dir / "manifest.json"
    if not manifest.exists():
        print("Warning: manifest.json not found in artifact directory; skipping manifest validation")
        return True
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Invalid manifest.json: {exc}", file=sys.stderr)
        return False

    # Basic validation: if manifest lists files, ensure they exist
    files = data.get("files") or data.get("artifacts") or []
    missing = []
    for f in files:
        p = artifact_dir / f
        if not p.exists():
            missing.append(f)
    if missing:
        print(f"Manifest validation failed, missing files: {missing}", file=sys.stderr)
        return False
    print("Manifest validation passed")
    return True


def _attempt_upload(folder: Path, repo: str, token: str, path_in_repo: str, retries: int, max_workers: Optional[int]):
    from huggingface_hub import create_repo, upload_folder

    create_repo(repo_id=repo, token=token, exist_ok=True)
    attempt = 0
    while True:
        try:
            upload_folder(
                folder_path=str(folder),
                path_in_repo=path_in_repo or "",
                repo_id=repo,
                token=token,
                max_workers=max_workers,
            )
            return True
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            attempt += 1
            if attempt > retries:
                print(f"Upload failed after {attempt} attempts: {exc}", file=sys.stderr)
                return False
            backoff = min(30, 2 ** attempt)
            print(f"Upload attempt {attempt} failed: {exc}. Retrying in {backoff}s...")
            time.sleep(backoff)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--repo", default=os.environ.get("HF_REPO") or os.environ.get("HF_MODEL_REPO"))
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--path-in-repo", default="")
    parser.add_argument("--dry-run", action="store_true", help="Validate credentials and manifest but do not upload")
    parser.add_argument("--private", action="store_true", help="Create repository as private (if supported)")
    parser.add_argument("--repo-type", choices=["model", "dataset", "space"], default="model")
    parser.add_argument("--commit-message", default="Publish model artifacts from CI")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=None)
    args = parser.parse_args(argv)

    if not args.token or not args.repo:
        print("HF_TOKEN and HF_REPO/HF_MODEL_REPO are required.", file=sys.stderr)
        return 2
    if not args.artifact_dir.is_dir():
        print(f"Artifact directory not found: {args.artifact_dir}", file=sys.stderr)
        return 2

    # Manifest validation
    ok = _validate_manifest(args.artifact_dir)
    if not ok:
        return 3

    if args.dry_run:
        print("Dry-run: credentials present and manifest validated. Skipping upload.")
        print(f"Would publish to: {args.repo} (type={args.repo_type})")
        return 0

    print(f"Publishing {args.artifact_dir} to {args.repo} (type={args.repo_type})")
    success = _attempt_upload(args.artifact_dir, args.repo, args.token, args.path_in_repo, args.retries, args.max_workers)
    if not success:
        return 4

    print(f"Published {args.artifact_dir} to {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
