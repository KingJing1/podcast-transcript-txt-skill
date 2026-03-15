#!/usr/bin/env python3
"""Unified wrapper for the persistent local podcast transcript runtime.

This script does not maintain a second transcription stack.
It forwards all real work to the single runtime configured at:
  /Users/jing/Desktop/podcast_transcripts/runtime.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


CONFIG_PATH = Path("/Users/jing/Desktop/podcast_transcripts/runtime.json")
RUNTIME_SCRIPT = Path("/Users/jing/Desktop/podcast_transcripts/transcribe_episode.py")


def load_runtime_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"missing runtime config: {CONFIG_PATH}")
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return data


def bootstrap_models(models: list[str], runtime: dict) -> int:
    model_cache_dir = Path(runtime["model_cache_dir"])
    model_cache_dir.mkdir(parents=True, exist_ok=True)
    for model in models:
        target = model_cache_dir / f"{model}.pt"
        if target.exists():
            print(f"MODEL_OK\t{target}")
            continue
        cmd = [
            runtime["venv_python"],
            "-c",
            (
                "import whisper; "
                f"whisper.load_model('{model}', download_root=r'{runtime['model_cache_dir']}')"
            ),
        ]
        print(f"MODEL_DL\t{model}\t->\t{target}")
        return subprocess.run(cmd).returncode
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export podcast transcript to TXT using the persistent local runtime")
    parser.add_argument("--input", action="append", help="Episode URL, audio URL, or local audio path")
    parser.add_argument("--out-dir", help="Output directory")
    parser.add_argument("--asr-model", default="small", choices=("small", "medium"))
    parser.add_argument("--page-text-fallback", default="auto", choices=("auto", "off"))
    parser.add_argument("--bootstrap-models", nargs="+")
    parser.add_argument("--emit-meta", action="store_true")
    args = parser.parse_args()

    runtime = load_runtime_config()
    if args.bootstrap_models:
        return bootstrap_models(args.bootstrap_models, runtime)
    if not args.input:
        parser.error("at least one --input is required (or use --bootstrap-models)")

    failures = 0
    for raw in args.input:
        cmd = [
            runtime["venv_python"],
            str(RUNTIME_SCRIPT),
            "--input",
            raw,
            "--model",
            args.asr_model,
            "--out-dir",
            args.out_dir or runtime["output_dir"],
        ]
        if args.emit_meta:
            cmd.append("--emit-meta")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout.strip())
        if proc.returncode != 0:
            failures += 1
            detail = proc.stderr.strip() or "runtime failed"
            print(f"FAIL\t{raw}\t{detail}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
