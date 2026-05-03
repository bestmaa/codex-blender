#!/usr/bin/env python3
"""Run a small live smoke test against the local Blender bridge."""

from __future__ import annotations

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
    "examples/create_table_model.json",
    "examples/apply_scaled_wood_texture.json",
    "examples/add_reference_image.json",
    "examples/render_scene.json",
    "examples/save_blend.json",
]


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


def run_example(relative_path: str) -> None:
    payload = load_example(relative_path)
    timeout = payload.get("params", {}).get("timeout_seconds", 300)
    result = request_json("POST", "/command", payload, timeout=timeout)
    if not result.get("ok"):
        raise RuntimeError(f"{relative_path} failed: {json.dumps(result, sort_keys=True)}")
    print(f"OK: {relative_path}")


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

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
