#!/usr/bin/env python3
"""Convert and quantize a model into GGUF artifacts using llama.cpp tools."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "models" / "gguf"
DEFAULT_QUANT = "Q4_K_M"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], dry_run: bool) -> None:
    print("+ " + " ".join(command))
    if dry_run:
        return
    subprocess.run(command, check=True)


def executable_name(name: str) -> str:
    if platform.system().lower().startswith("win"):
        return f"{name}.exe"
    return name


def find_llama_tool(
    llama_cpp_dir: Path | None, explicit: str | None, names: list[str], dry_run: bool
) -> str:
    if explicit:
        return explicit

    search_dirs: list[Path] = []
    if llama_cpp_dir:
        search_dirs.extend(
            [
                llama_cpp_dir,
                llama_cpp_dir / "build" / "bin",
                llama_cpp_dir / "bin",
            ]
        )

    for directory in search_dirs:
        for name in names:
            candidate = directory / name
            if candidate.exists():
                return str(candidate)

    for name in names:
        found = shutil.which(name)
        if found:
            return found

    if dry_run:
        return names[0]

    raise RuntimeError(f"Could not find llama.cpp tool; tried: {', '.join(names)}")


def convert_to_gguf(input_path: Path, out_dir: Path, model_name: str, args: argparse.Namespace) -> Path:
    if input_path.suffix.lower() == ".gguf":
        target = out_dir / f"{model_name}.f16.gguf"
        if input_path.resolve() != target.resolve() and not args.dry_run:
            shutil.copyfile(input_path, target)
        elif args.dry_run:
            print(f"+ copy {input_path} {target}")
        return target

    converter = find_llama_tool(
        args.llama_cpp_dir,
        args.convert_script,
        ["convert_hf_to_gguf.py", "convert.py"],
        args.dry_run,
    )
    output = out_dir / f"{model_name}.f16.gguf"
    command = [
        sys.executable,
        converter,
        str(input_path),
        "--outfile",
        str(output),
        "--outtype",
        args.outtype,
    ]
    run_command(command, args.dry_run)
    return output


def quantize_gguf(base_gguf: Path, out_dir: Path, model_name: str, args: argparse.Namespace) -> list[Path]:
    quantize = find_llama_tool(
        args.llama_cpp_dir,
        args.quantize_bin,
        [
            executable_name("llama-quantize"),
            executable_name("quantize"),
        ],
        args.dry_run,
    )
    artifacts = []
    for quant in args.quantization:
        output = out_dir / f"{model_name}.{quant}.gguf"
        run_command([quantize, str(base_gguf), str(output), quant], args.dry_run)
        artifacts.append(output)
    return artifacts


def write_manifest(paths: list[Path], out_dir: Path, model_name: str, dry_run: bool) -> Path:
    manifest_path = out_dir / f"{model_name}.gguf-manifest.json"
    artifacts = []
    for path in paths:
        if dry_run:
            artifacts.append({"file": path.name, "sha256": None, "bytes": None})
            continue
        artifacts.append(
            {
                "file": path.name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "model": model_name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifacts": artifacts,
    }
    if dry_run:
        print(json.dumps(manifest, indent=2))
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Wrote {manifest_path}")
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="HF model directory or source GGUF file")
    parser.add_argument("--out-dir", type=Path, default=Path(os.environ.get("GGUF_OUT_DIR", DEFAULT_OUT_DIR)))
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--quantization", action="append", default=[], help="GGUF quantization, repeatable")
    parser.add_argument("--outtype", default="f16", choices=["f16", "f32", "q8_0"])
    llama_cpp_env = os.environ.get("LLAMA_CPP_DIR")
    parser.add_argument("--llama-cpp-dir", type=Path, default=Path(llama_cpp_env) if llama_cpp_env else None)
    parser.add_argument("--convert-script", default=os.environ.get("LLAMA_CPP_CONVERT"))
    parser.add_argument("--quantize-bin", default=os.environ.get("LLAMA_CPP_QUANTIZE"))
    parser.add_argument("--keep-f16", action="store_true", help="Include the intermediate f16 GGUF in the manifest")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    args.quantization = args.quantization or [DEFAULT_QUANT]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_name = args.model_name or args.input.stem

    try:
        base_gguf = convert_to_gguf(args.input, args.out_dir, model_name, args)
        artifacts = quantize_gguf(base_gguf, args.out_dir, model_name, args)
        manifest_paths = ([base_gguf] if args.keep_f16 else []) + artifacts
        write_manifest(manifest_paths, args.out_dir, model_name, args.dry_run)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"GGUF packaging command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"GGUF packaging failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
