#!/usr/bin/env python3
"""Publish a prepared artifact directory to Hugging Face Hub."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--repo", default=os.environ.get("HF_REPO") or os.environ.get("HF_MODEL_REPO"))
    parser.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    parser.add_argument("--path-in-repo", default="")
    args = parser.parse_args(argv)

    if not args.token or not args.repo:
        print("HF_TOKEN and HF_REPO/HF_MODEL_REPO are required.", file=sys.stderr)
        return 2
    if not args.artifact_dir.is_dir():
        print(f"Artifact directory not found: {args.artifact_dir}", file=sys.stderr)
        return 2

    from huggingface_hub import create_repo, upload_folder

    create_repo(repo_id=args.repo, token=args.token, exist_ok=True)
    upload_folder(
        folder_path=str(args.artifact_dir),
        path_in_repo=args.path_in_repo,
        repo_id=args.repo,
        token=args.token,
    )
    print(f"Published {args.artifact_dir} to {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
