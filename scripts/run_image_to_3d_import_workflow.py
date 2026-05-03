#!/usr/bin/env python3
"""Run image-to-3D generation and import the output through the Blender bridge."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def call_bridge(base_url: str, payload: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/command"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_bridge(base_url: str, timeout: float = 5.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/health", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "ok": False,
            "errorType": "BridgeUnavailable",
            "message": f"Could not reach Blender bridge at {base_url}: {exc}",
        }


def wait_for_output(path: Path, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() <= deadline:
        if path.exists():
            return True
        time.sleep(0.25)
    return path.exists()


def run_provider(job_path: Path, job: dict[str, Any], timeout_seconds: float, dry_run: bool) -> dict[str, Any]:
    output = project_path(job["output"])
    mock_output_from = job.get("mock_output_from")
    if mock_output_from:
        source = project_path(str(mock_output_from))
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "mode": "mock",
                "source": str(source),
                "output": str(output),
            }
        if not source.exists():
            return {
                "ok": False,
                "errorType": "MockOutputNotFound",
                "message": f"Mock generated model does not exist: {source}",
            }
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        return {
            "ok": True,
            "mode": "mock",
            "message": "Copied mock generated model.",
            "source": str(source),
            "output": str(output),
        }

    command = [sys.executable, str(ROOT / "scripts" / "run_image_to_3d_job.py"), str(job_path)]
    if dry_run:
        command.append("--dry-run")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "errorType": "ProviderReturnedInvalidJson", "stdout": completed.stdout}
    payload["returncode"] = completed.returncode
    if completed.stderr:
        payload["stderr"] = completed.stderr
    return payload


def build_plan(job: dict[str, Any], output: Path) -> list[dict[str, Any]]:
    import_options = job.get("import_options", {})
    plan = [
        {
            "action": "import_asset",
            "params": {
                "path": str(output),
                "location": import_options.get("location", [0, 0, 0]),
                "rotation": import_options.get("rotation", [0, 0, 0]),
                "scale": import_options.get("scale", 1.0),
            },
        }
    ]
    if import_options.get("fit_to_bounds", True):
        plan.append(
            {
                "action": "fit_object_to_bounds",
                "params": {
                    "object": "<imported object>",
                    "target_size": import_options.get("target_size", [1, 1, 1]),
                    "target_location": import_options.get("target_location", [0, 0, 0]),
                    "align_to_floor": import_options.get("align_to_floor", True),
                },
            }
        )
    target = import_options.get("camera_target", import_options.get("target_location", [0, 0, 0]))
    plan.append(
        {
            "action": "setup_reference_camera",
            "params": {
                "reference_object": "<imported object>",
                "camera_location": import_options.get("camera_location", [3.2, -4.2, 2.4]),
                "target": target,
                "lens": import_options.get("camera_lens", 45),
                "resolution": import_options.get("resolution", [1280, 720]),
            },
        }
    )
    if import_options.get("render_preview", False):
        plan.append(
            {
                "action": "render_scene",
                "params": {
                    "output": import_options.get("preview_output", "renders/image_to_3d_preview.png"),
                    "resolution": import_options.get("resolution", [1280, 720]),
                    "samples": import_options.get("samples", 32),
                },
            }
        )
    return plan


def execute_import_workflow(args: argparse.Namespace) -> int:
    job_path = project_path(args.job)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    output = project_path(job["output"])
    wait_seconds = float(job.get("wait_seconds", args.wait_seconds))
    plan = build_plan(job, output)

    if args.dry_run:
        provider = run_provider(job_path, job, wait_seconds, dry_run=True)
        print_json({"ok": True, "dry_run": True, "provider": provider, "output": str(output), "plan": plan})
        return 0

    provider = run_provider(job_path, job, wait_seconds, dry_run=False)
    if not provider.get("ok"):
        print_json({"ok": False, "errorType": "ProviderStepFailed", "provider": provider})
        return 1
    if not wait_for_output(output, wait_seconds):
        print_json(
            {
                "ok": False,
                "errorType": "GeneratedModelMissing",
                "message": f"Provider finished but output did not appear: {output}",
                "provider": provider,
            }
        )
        return 1

    import_options = job.get("import_options", {})
    if not import_options.get("import_after_generate", True):
        print_json({"ok": True, "provider": provider, "output": str(output), "imported": None})
        return 0

    health = check_bridge(args.bridge_url)
    if health.get("ok") is False:
        print_json({"ok": False, "errorType": "BridgeUnavailable", "health": health, "provider": provider})
        return 1

    import_result = call_bridge(args.bridge_url, plan[0])
    imported_objects = import_result.get("objects", [])
    imported_object = imported_objects[0] if imported_objects else None
    if not import_result.get("ok") or not imported_object:
        print_json({"ok": False, "errorType": "ImportStepFailed", "import": import_result, "provider": provider})
        return 1

    fit_result = None
    camera_result = None
    render_result = None
    for step in plan[1:]:
        params = step["params"]
        if params.get("object") == "<imported object>":
            params["object"] = imported_object
        if params.get("reference_object") == "<imported object>":
            params["reference_object"] = imported_object
        result = call_bridge(args.bridge_url, step)
        if step["action"] == "fit_object_to_bounds":
            fit_result = result
        elif step["action"] == "setup_reference_camera":
            camera_result = result
        elif step["action"] == "render_scene":
            render_result = result
        if not result.get("ok"):
            print_json({"ok": False, "errorType": "BridgeStepFailed", "step": step["action"], "result": result})
            return 1

    print_json(
        {
            "ok": True,
            "provider": provider,
            "output": str(output),
            "imported_object": imported_object,
            "import": import_result,
            "fit": fit_result,
            "camera": camera_result,
            "render": render_result,
        }
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate, import, fit, camera-frame, and preview an image-to-3D job.")
    parser.add_argument("job", help="Path to an image-to-3D job JSON file.")
    parser.add_argument("--bridge-url", default="http://127.0.0.1:8765", help="Running Codex Blender bridge URL.")
    parser.add_argument("--wait-seconds", type=float, default=30.0, help="How long to wait for generated output.")
    parser.add_argument("--dry-run", action="store_true", help="Print provider/import plan without touching Blender.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return execute_import_workflow(parse_args(argv or sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
