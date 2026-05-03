#!/usr/bin/env python3
"""Run a live BlenderMCP compatibility smoke test against the local bridge."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_URL = os.environ.get("CODEX_BLENDER_BRIDGE_URL", "http://127.0.0.1:8765").rstrip("/")

EXAMPLE_SEQUENCE = [
    "examples/blendermcp/get_scene_info.json",
    "examples/blendermcp/create_cube.json",
    "examples/blendermcp/render_scene.json",
    "examples/blendermcp/save_scene.json",
]


def load_adapter():
    adapter_path = ROOT / "bridge" / "blendermcp_adapter.py"
    spec = importlib.util.spec_from_file_location("blendermcp_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load BlenderMCP adapter from {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.translate_blendermcp_payload


translate_blendermcp_payload = load_adapter()


def request_json(method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 300) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BRIDGE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_example(relative_path: str) -> dict[str, Any]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def normalize_paths(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    params = payload.setdefault("params", {})
    if action in {"render_scene", "save_blend", "export_glb", "export_obj"}:
        output = params.get("output")
        if isinstance(output, str) and output and not Path(output).is_absolute() and not output.startswith("//"):
            params["output"] = str((ROOT / output).resolve())
    return payload


def run_example(relative_path: str) -> None:
    compatibility_payload = load_example(relative_path)
    native_payload = translate_blendermcp_payload(compatibility_payload)
    if native_payload.get("ok") is False:
        raise RuntimeError(f"{relative_path} did not translate: {json.dumps(native_payload, sort_keys=True)}")
    native_payload = normalize_paths(native_payload)
    timeout = native_payload.get("params", {}).get("timeout_seconds", 300)
    result = request_json("POST", "/command", native_payload, timeout=timeout)
    if not result.get("ok"):
        raise RuntimeError(f"{relative_path} failed: {json.dumps(result, sort_keys=True)}")
    print(f"OK: {relative_path} -> {native_payload['action']}")


def main() -> int:
    try:
        health = request_json("GET", "/health", timeout=10)
        if not health.get("ok"):
            raise RuntimeError(f"Bridge health check failed: {json.dumps(health, sort_keys=True)}")
        print(f"OK: bridge health at {BRIDGE_URL}")

        for relative_path in EXAMPLE_SEQUENCE:
            run_example(relative_path)
    except (OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("BlenderMCP compatibility smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
