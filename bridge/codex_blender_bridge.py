#!/usr/bin/env python3
"""Send JSON commands to the Codex Blender add-on."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import importlib.util
from pathlib import Path

try:
    from blendermcp_adapter import translate_blendermcp_payload
except ModuleNotFoundError:
    adapter_path = Path(__file__).with_name("blendermcp_adapter.py")
    spec = importlib.util.spec_from_file_location("blendermcp_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    translate_blendermcp_payload = adapter.translate_blendermcp_payload


DEFAULT_URL = "http://127.0.0.1:8765/command"


def load_payload(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def normalize_command_paths(payload: dict, base_dir: Path) -> dict:
    action = payload.get("action")
    if action not in {"render_scene", "save_blend", "export_glb", "export_obj", "import_asset", "add_reference_image", "apply_texture_material"}:
        return payload

    params = payload.setdefault("params", {})
    key = "path" if action in {"import_asset", "add_reference_image", "apply_texture_material"} else "output"
    value = params.get(key)
    if not isinstance(value, str) or not value or value.startswith("//"):
        value = None

    if value is not None:
        path = Path(value)
        if not path.is_absolute():
            params[key] = str((base_dir / path).resolve())
    if action == "apply_texture_material":
        for texture_key in ("base_color_path", "roughness_path", "normal_path", "metallic_path", "alpha_path"):
            texture_value = params.get(texture_key)
            if isinstance(texture_value, str) and texture_value and not texture_value.startswith("//"):
                texture_path = Path(texture_value)
                if not texture_path.is_absolute():
                    params[texture_key] = str((base_dir / texture_path).resolve())
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
        payload = normalize_command_paths(translate_blendermcp_payload(load_payload(args.payload)), Path.cwd())
        if payload.get("ok") is False:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 1
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
