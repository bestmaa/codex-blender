#!/usr/bin/env python3
"""Send JSON commands to the Codex Blender add-on."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URL = "http://127.0.0.1:8765/command"


def load_payload(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def normalize_command_paths(payload: dict, base_dir: Path) -> dict:
    action = payload.get("action")
    if action not in {"render_scene", "save_blend", "import_asset", "add_reference_image", "apply_texture_material"}:
        return payload

    params = payload.setdefault("params", {})
    key = "path" if action in {"import_asset", "add_reference_image", "apply_texture_material"} else "output"
    value = params.get(key)
    if not isinstance(value, str) or not value or value.startswith("//"):
        return payload

    path = Path(value)
    if not path.is_absolute():
        params[key] = str((base_dir / path).resolve())
    return payload


def send_command(payload: dict, url: str, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a command to Blender.")
    parser.add_argument("payload", help="Path to a JSON command file, or inline JSON.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Bridge URL. Default: {DEFAULT_URL}")
    parser.add_argument("--timeout", type=int, default=300, help="Request timeout in seconds. Default: 300")
    args = parser.parse_args()

    try:
        payload = normalize_command_paths(load_payload(args.payload), Path.cwd())
        result = send_command(payload, args.url, args.timeout)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"Could not reach Blender bridge: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
