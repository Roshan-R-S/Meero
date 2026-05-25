#!/usr/bin/env python3
"""Small secret scanner for CI and pre-commit."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".pytest_cache",
}

PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("hf_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}"
        ),
    ),
]


def git_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line) for line in output.splitlines() if line.strip()]


def walk_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        files.append(path)
    return files


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in chunk


def scan_file(path: Path) -> list[tuple[str, int, str]]:
    if is_binary(path):
        return []
    findings = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    for number, line in enumerate(lines, start=1):
        if "pragma: allowlist secret" in line:
            continue
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append((name, number, line.strip()[:160]))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--all-files", action="store_true", help="Scan all files under the current directory")
    args = parser.parse_args(argv)

    if args.paths:
        paths = args.paths
    elif args.all_files:
        paths = walk_files(Path("."))
    else:
        paths = git_files()

    failures = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        for name, line_no, preview in scan_file(path):
            failures.append(f"{path}:{line_no}: {name}: {preview}")

    if failures:
        print("Potential secrets found:", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        print("Add 'pragma: allowlist secret' only for intentional test fixtures.", file=sys.stderr)
        return 1

    print("No obvious secrets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
