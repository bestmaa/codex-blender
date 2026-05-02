#!/usr/bin/env python3
"""Minimal MCP server for the local Codex Blender bridge."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BRIDGE_URL = os.environ.get("BLENDER_BRIDGE_URL", "http://127.0.0.1:8765").rstrip("/")
OUTPUT_BASE_DIR = Path(os.environ.get("BLENDER_OUTPUT_BASE_DIR", os.getcwd()))


def json_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


TOOLS = [
    {
        "name": "blender_health",
        "description": "Check whether the local Blender bridge is reachable.",
        "inputSchema": json_schema({}),
    },
    {
        "name": "blender_create_room",
        "description": "Create the starter room scene in Blender.",
        "inputSchema": json_schema(
            {
                "style": {
                    "type": "string",
                    "description": "Room style label to pass to Blender.",
                    "default": "modern_neon",
                }
            }
        ),
    },
    {
        "name": "blender_render_scene",
        "description": "Render the current Blender scene from the active camera to a PNG file.",
        "inputSchema": json_schema(
            {
                "output": {
                    "type": "string",
                    "description": "Output PNG path, relative to the plugin folder or absolute.",
                    "default": "renders/room.png",
                },
                "resolution": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Render resolution as [width, height].",
                    "default": [1280, 720],
                },
                "samples": {
                    "type": "integer",
                    "description": "Cycles sample count when the scene uses Cycles.",
                    "default": 32,
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": "Maximum time to wait for Blender to finish rendering.",
                    "default": 300,
                },
            }
        ),
    },
    {
        "name": "blender_create_outdoor_scene",
        "description": "Create an outdoor road scene with trees, street lights, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "road_length": {
                    "type": "number",
                    "description": "Road length in Blender units.",
                    "default": 32,
                },
                "road_width": {
                    "type": "number",
                    "description": "Road width in Blender units.",
                    "default": 5,
                },
                "tree_count": {
                    "type": "integer",
                    "description": "Number of simple trees to place along both sides.",
                    "default": 12,
                },
                "street_light_count": {
                    "type": "integer",
                    "description": "Number of street lights to place along both sides.",
                    "default": 6,
                },
                "style": {
                    "type": "string",
                    "description": "Scene style label.",
                    "default": "clean_suburban",
                },
            }
        ),
    },
    {
        "name": "blender_save_blend",
        "description": "Save the current Blender scene to a .blend file.",
        "inputSchema": json_schema(
            {
                "output": {
                    "type": "string",
                    "description": "Output .blend path, relative to the plugin folder or absolute.",
                    "default": "scenes/scene.blend",
                }
            }
        ),
    },
    {
        "name": "blender_inspect_rig",
        "description": "Return armature and bone names from the current Blender scene.",
        "inputSchema": json_schema({}),
    },
    {
        "name": "blender_command",
        "description": "Send a raw trusted JSON command to the local Blender bridge.",
        "inputSchema": json_schema(
            {
                "payload": {
                    "type": "object",
                    "description": "Raw Blender bridge payload, for example {'action': 'ping'}.",
                }
            },
            required=["payload"],
        ),
    },
]


def call_http(path: str, payload: dict[str, Any] | None = None, timeout: float = 300) -> dict[str, Any]:
    url = f"{BRIDGE_URL}{path}"
    try:
        if payload is None:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"Could not reach Blender bridge: {exc}"}


def normalize_output_path(value: Any) -> Any:
    if not isinstance(value, str) or not value or value.startswith("//"):
        return value

    output_path = Path(value)
    if output_path.is_absolute():
        return value
    return str((OUTPUT_BASE_DIR / output_path).resolve())


def call_tool(name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if name == "blender_health":
        result = call_http("/health")
    elif name == "blender_create_room":
        result = call_http(
            "/command",
            {"action": "create_room", "params": {"style": arguments.get("style", "modern_neon")}},
        )
    elif name == "blender_render_scene":
        params = {
            "output": normalize_output_path(arguments.get("output", "renders/room.png")),
            "resolution": arguments.get("resolution", [1280, 720]),
            "samples": arguments.get("samples", 32),
            "timeout_seconds": arguments.get("timeout_seconds", 300),
        }
        result = call_http("/command", {"action": "render_scene", "params": params}, timeout=params["timeout_seconds"])
    elif name == "blender_create_outdoor_scene":
        params = {
            "road_length": arguments.get("road_length", 32),
            "road_width": arguments.get("road_width", 5),
            "tree_count": arguments.get("tree_count", 12),
            "street_light_count": arguments.get("street_light_count", 6),
            "style": arguments.get("style", "clean_suburban"),
        }
        result = call_http("/command", {"action": "create_outdoor_scene", "params": params})
    elif name == "blender_save_blend":
        params = {"output": normalize_output_path(arguments.get("output", "scenes/scene.blend"))}
        result = call_http("/command", {"action": "save_blend", "params": params})
    elif name == "blender_inspect_rig":
        result = call_http("/command", {"action": "inspect_rig"})
    elif name == "blender_command":
        payload = arguments.get("payload")
        if not isinstance(payload, dict):
            result = {"ok": False, "error": "payload must be an object"}
        else:
            if payload.get("action") in {"render_scene", "save_blend"}:
                params = payload.setdefault("params", {})
                default_output = "scenes/scene.blend" if payload.get("action") == "save_blend" else "renders/room.png"
                params["output"] = normalize_output_path(params.get("output", default_output))
            timeout = payload.get("params", {}).get("timeout_seconds", 300)
            result = call_http("/command", payload, timeout=timeout)
    else:
        result = {"ok": False, "error": f"Unknown tool: {name}"}

    return result, not bool(result.get("ok"))


def make_response(request_id: Any, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result or {}
    return response


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        return make_response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "codex-blender", "version": "0.6.0"},
            },
        )
    if method == "tools/list":
        return make_response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = message.get("params") or {}
        result, is_error = call_tool(params.get("name", ""), params.get("arguments") or {})
        return make_response(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result, indent=2, sort_keys=True)}],
                "isError": is_error,
            },
        )

    if request_id is None:
        return None
    return make_response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_request(message)
        except Exception as exc:
            response = make_response(None, error={"code": -32603, "message": str(exc)})

        if response is not None:
            print(json.dumps(response), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
