#!/usr/bin/env python3
"""Helper for rotating CI secrets into GitHub Actions."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


def run(command: list[str], dry_run: bool) -> None:
    redacted = ["***" if index == len(command) - 1 and "--body" in command else part for index, part in enumerate(command)]
    print("+ " + " ".join(redacted))
    if not dry_run:
        subprocess.run(command, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secret", action="append", required=True, help="GitHub Actions secret name; repeatable")
    parser.add_argument("--repo", help="owner/repo target for gh secret set")
    parser.add_argument("--org", help="GitHub organization target for org-level secrets")
    parser.add_argument("--env-prefix", default="NEW_", help="Read each new value from this env prefix plus secret name")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.repo and args.org:
        print("Use either --repo or --org, not both.", file=sys.stderr)
        return 2

    missing = [name for name in args.secret if not os.environ.get(f"{args.env_prefix}{name}")]
    if missing:
        joined = ", ".join(f"{args.env_prefix}{name}" for name in missing)
        print(f"Missing replacement secret value(s): {joined}", file=sys.stderr)
        return 2

    try:
        for name in args.secret:
            value = os.environ[f"{args.env_prefix}{name}"]
            command = ["gh", "secret", "set", name]
            if args.repo:
                command.extend(["--repo", args.repo])
            if args.org:
                command.extend(["--org", args.org])
            command.extend(["--body", value])
            run(command, args.dry_run)
    except subprocess.CalledProcessError as exc:
        return exc.returncode

    print("Secrets updated. Revoke the old provider tokens after dependent workflows pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
