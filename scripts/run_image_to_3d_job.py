#!/usr/bin/env python3
"""Run a provider-neutral image-to-3D job through a configured local command."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_COMMAND = "CODEX_BLENDER_IMAGE_TO_3D_COMMAND"
PLACEHOLDER_PARTS = ("path/to/", "path\\to\\", "<", ">")


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def command_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(part) for part in value if str(part)]
    if isinstance(value, str) and value.strip():
        return shlex.split(value)
    return []


def is_placeholder_command(command: list[str]) -> bool:
    return any(token in part for part in command for token in PLACEHOLDER_PARTS)


def resolve_provider_command(args: argparse.Namespace, job: dict[str, Any]) -> tuple[list[str], str]:
    sources = [
        ("--provider-command", args.provider_command),
        ("job.provider_command", job.get("provider_command")),
        (ENV_COMMAND, os.environ.get(ENV_COMMAND)),
    ]
    for source, value in sources:
        command = command_from_value(value)
        if command:
            return command, source
    return [], ""


def missing_provider_error(job_path: Path, job: dict[str, Any], source: str = "") -> dict[str, Any]:
    provider = job.get("provider", "local_stub")
    detail = f"Configured command from {source} is a placeholder." if source else "No provider command is configured."
    return {
        "ok": False,
        "errorType": "MissingImageTo3DProviderCommand",
        "provider": provider,
        "message": "Local image-to-3D generation needs a separate provider executable or script.",
        "detail": detail,
        "expected_command": (
            "your-provider --job JOB.json --input-image IMAGE.png --output MODEL.glb "
            "--quality preview --provider local_stub"
        ),
        "setup": [
            "Install or create a local image-to-3D provider outside this repository.",
            "Pass it with --provider-command, job.provider_command, or CODEX_BLENDER_IMAGE_TO_3D_COMMAND.",
            "The provider must write the model file requested by the job output field.",
            "Do not place model weights or vendor secrets in this repository.",
        ],
        "job": str(job_path),
    }


def build_provider_args(command: list[str], job_path: Path, job: dict[str, Any]) -> list[str]:
    input_image = project_path(job["input_image"])
    output = project_path(job["output"])
    provider_args = [
        "--job",
        str(job_path),
        "--input-image",
        str(input_image),
        "--output",
        str(output),
        "--quality",
        str(job["quality"]),
        "--provider",
        str(job["provider"]),
    ]
    if job.get("prompt"):
        provider_args.extend(["--prompt", str(job["prompt"])])
    if job.get("metadata_output"):
        provider_args.extend(["--metadata-output", str(project_path(job["metadata_output"]))])
    if job.get("seed") is not None:
        provider_args.extend(["--seed", str(job["seed"])])
    return command + provider_args


def write_metadata_if_missing(job: dict[str, Any], command_source: str, returncode: int) -> None:
    metadata_output = job.get("metadata_output")
    if not metadata_output:
        return
    path = project_path(metadata_output)
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": job["provider"],
        "source_image": job["input_image"],
        "output": job["output"],
        "quality": job["quality"],
        "command_source": command_source,
        "returncode": returncode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": "Metadata created by the Codex Blender local provider runner.",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_job(args: argparse.Namespace) -> int:
    job_path = project_path(args.job)
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print_json({"ok": False, "errorType": "JobFileNotFound", "message": f"Job file not found: {job_path}"})
        return 1
    except json.JSONDecodeError as exc:
        print_json({"ok": False, "errorType": "InvalidJobJson", "message": str(exc), "job": str(job_path)})
        return 1

    command, source = resolve_provider_command(args, job)
    if not command or is_placeholder_command(command):
        print_json(missing_provider_error(job_path, job, source))
        return 2

    input_image = project_path(job["input_image"])
    if not input_image.exists():
        print_json(
            {
                "ok": False,
                "errorType": "InputImageNotFound",
                "message": f"Input image not found: {input_image}",
                "job": str(job_path),
            }
        )
        return 1

    output = project_path(job["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    full_command = build_provider_args(command, job_path, job)
    if args.dry_run:
        print_json({"ok": True, "dry_run": True, "command": full_command, "command_source": source})
        return 0

    try:
        completed = subprocess.run(
            full_command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=float(job.get("timeout_seconds", args.timeout_seconds)),
            check=False,
        )
    except FileNotFoundError:
        print_json(missing_provider_error(job_path, job, source))
        return 2
    except subprocess.TimeoutExpired as exc:
        print_json(
            {
                "ok": False,
                "errorType": "ProviderTimeout",
                "message": f"Provider timed out after {exc.timeout} seconds.",
                "command_source": source,
            }
        )
        return 3

    if completed.returncode != 0:
        print_json(
            {
                "ok": False,
                "errorType": "ProviderCommandFailed",
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "command_source": source,
            }
        )
        return completed.returncode or 1

    if not output.exists():
        print_json(
            {
                "ok": False,
                "errorType": "ProviderDidNotCreateOutput",
                "message": f"Provider completed but did not create output: {output}",
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "command_source": source,
            }
        )
        return 4

    write_metadata_if_missing(job, source, completed.returncode)
    print_json(
        {
            "ok": True,
            "provider": job["provider"],
            "output": str(output),
            "format": output.suffix.lower().lstrip("."),
            "metadata_output": str(project_path(job["metadata_output"])) if job.get("metadata_output") else None,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command_source": source,
        }
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an image-to-3D job with a configured local provider command.")
    parser.add_argument("job", help="Path to an image-to-3D job JSON file.")
    parser.add_argument("--provider-command", help="Provider executable/command. Overrides job and env config.")
    parser.add_argument("--timeout-seconds", type=float, default=900.0, help="Fallback timeout when the job omits one.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command that would run without executing it.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run_job(parse_args(argv or sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
