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
        "name": "blender_create_table_model",
        "description": "Create a modern wooden table model with rounded tabletop, tapered legs, wood grain, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "length": {
                    "type": "number",
                    "description": "Table length in Blender units.",
                    "default": 3.6,
                },
                "width": {
                    "type": "number",
                    "description": "Table width in Blender units.",
                    "default": 2.0,
                },
                "height": {
                    "type": "number",
                    "description": "Table height in Blender units.",
                    "default": 1.55,
                },
                "top_thickness": {
                    "type": "number",
                    "description": "Tabletop thickness in Blender units.",
                    "default": 0.24,
                },
                "corner_roundness": {
                    "type": "number",
                    "description": "Bevel amount for the tabletop corners.",
                    "default": 0.14,
                },
                "include_grain": {
                    "type": "boolean",
                    "description": "Add raised subtle wood grain lines on the tabletop.",
                    "default": True,
                },
                "wood_color": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Wood color as [r, g, b, a].",
                    "default": [0.78, 0.47, 0.25, 1],
                },
                "style": {
                    "type": "string",
                    "description": "Style label to return in the result.",
                    "default": "modern_wood",
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
        "name": "blender_import_asset",
        "description": "Import a local 3D asset into the current Blender scene.",
        "inputSchema": json_schema(
            {
                "path": {
                    "type": "string",
                    "description": "Asset path. Supports .glb, .gltf, .fbx, and .obj.",
                },
                "location": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Import location as [x, y, z].",
                    "default": [0, 0, 0],
                },
                "rotation": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Import rotation in radians as [x, y, z].",
                    "default": [0, 0, 0],
                },
                "scale": {
                    "description": "Uniform number scale or [x, y, z] scale.",
                    "default": 1.0,
                },
            },
            required=["path"],
        ),
    },
    {
        "name": "blender_add_reference_image",
        "description": "Add a local image as a reference plane in the current Blender scene.",
        "inputSchema": json_schema(
            {
                "path": {
                    "type": "string",
                    "description": "Image path. Supports image formats Blender can load, such as .png and .jpg.",
                },
                "name": {
                    "type": "string",
                    "description": "Optional reference plane object name.",
                    "default": "reference image",
                },
                "location": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Plane location as [x, y, z].",
                    "default": [0, 2.2, 1.4],
                },
                "rotation": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Plane rotation in radians as [x, y, z].",
                    "default": [1.5708, 0, 0],
                },
                "width": {
                    "type": "number",
                    "description": "Reference plane width in Blender units.",
                    "default": 3.0,
                },
                "height": {
                    "type": "number",
                    "description": "Optional explicit plane height. If omitted, image aspect ratio is preserved.",
                },
                "opacity": {
                    "type": "number",
                    "description": "Reference image opacity from 0.05 to 1.0.",
                    "default": 1.0,
                },
                "unlit": {
                    "type": "boolean",
                    "description": "Make the reference image visible independent of scene lighting.",
                    "default": True,
                },
            },
            required=["path"],
        ),
    },
    {
        "name": "blender_apply_texture_material",
        "description": "Apply a local image file as a texture material on an existing Blender object.",
        "inputSchema": json_schema(
            {
                "object": {
                    "type": "string",
                    "description": "Exact Blender object name to receive the material.",
                },
                "path": {
                    "type": "string",
                    "description": "Texture image path, such as assets/textures/wood.png.",
                },
                "material_name": {
                    "type": "string",
                    "description": "Optional material name.",
                    "default": "texture material",
                },
                "roughness": {
                    "type": "number",
                    "description": "Material roughness from 0 to 1.",
                    "default": 0.55,
                },
                "metallic": {
                    "type": "number",
                    "description": "Material metallic value from 0 to 1.",
                    "default": 0.0,
                },
                "opacity": {
                    "type": "number",
                    "description": "Material opacity from 0.05 to 1.0.",
                    "default": 1.0,
                },
                "texture_scale": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Texture mapping scale as [x, y].",
                    "default": [1.0, 1.0],
                },
                "texture_offset": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Texture mapping offset as [x, y].",
                    "default": [0.0, 0.0],
                },
                "texture_rotation": {
                    "type": "number",
                    "description": "Texture mapping rotation in radians.",
                    "default": 0.0,
                },
                "projection": {
                    "type": "string",
                    "description": "Texture coordinate projection: uv, generated, or object.",
                    "default": "uv",
                },
                "mode": {
                    "type": "string",
                    "description": "Use replace to clear existing materials, or append to add a material slot.",
                    "default": "replace",
                },
            },
            required=["object", "path"],
        ),
    },
    {
        "name": "blender_apply_material_preset",
        "description": "Apply a built-in material preset to an existing Blender object.",
        "inputSchema": json_schema(
            {
                "object": {
                    "type": "string",
                    "description": "Exact Blender object name to receive the material.",
                },
                "preset": {
                    "type": "string",
                    "description": "Preset name: wood_oak, fabric_soft, brushed_metal, glass_clear, or matte_plastic.",
                    "default": "wood_oak",
                },
                "material_name": {
                    "type": "string",
                    "description": "Optional material name.",
                    "default": "preset material",
                },
                "mode": {
                    "type": "string",
                    "description": "Use replace to clear existing materials, or append to add a material slot.",
                    "default": "replace",
                },
            },
            required=["object", "preset"],
        ),
    },
    {
        "name": "blender_create_scene_from_reference",
        "description": "Create an approximate Blender scene from a structured reference-image scene plan.",
        "inputSchema": json_schema(
            {
                "title": {"type": "string", "default": "reference scene"},
                "floor_color": {"type": "array", "items": {"type": "number"}, "default": [0.45, 0.43, 0.38, 1]},
                "floor_size": {"type": "array", "items": {"type": "number"}, "default": [8, 6, 0.08]},
                "objects": {
                    "type": "array",
                    "description": "Primitive scene objects inferred from a reference image.",
                    "items": {"type": "object"},
                    "default": [],
                },
                "camera_location": {"type": "array", "items": {"type": "number"}, "default": [5, -5, 3]},
                "camera_rotation": {"type": "array", "items": {"type": "number"}, "default": [1.0472, 0, 0.733]},
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


def normalize_input_path(value: Any) -> Any:
    return normalize_output_path(value)


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
    elif name == "blender_create_table_model":
        params = {
            "length": arguments.get("length", 3.6),
            "width": arguments.get("width", 2.0),
            "height": arguments.get("height", 1.55),
            "top_thickness": arguments.get("top_thickness", 0.24),
            "corner_roundness": arguments.get("corner_roundness", 0.14),
            "include_grain": arguments.get("include_grain", True),
            "wood_color": arguments.get("wood_color", [0.78, 0.47, 0.25, 1]),
            "style": arguments.get("style", "modern_wood"),
        }
        result = call_http("/command", {"action": "create_table_model", "params": params})
    elif name == "blender_save_blend":
        params = {"output": normalize_output_path(arguments.get("output", "scenes/scene.blend"))}
        result = call_http("/command", {"action": "save_blend", "params": params})
    elif name == "blender_import_asset":
        params = {
            "path": normalize_input_path(arguments.get("path")),
            "location": arguments.get("location", [0, 0, 0]),
            "rotation": arguments.get("rotation", [0, 0, 0]),
            "scale": arguments.get("scale", 1.0),
        }
        result = call_http("/command", {"action": "import_asset", "params": params})
    elif name == "blender_add_reference_image":
        params = {
            "path": normalize_input_path(arguments.get("path")),
            "name": arguments.get("name", "reference image"),
            "location": arguments.get("location", [0, 2.2, 1.4]),
            "rotation": arguments.get("rotation", [1.5708, 0, 0]),
            "width": arguments.get("width", 3.0),
            "opacity": arguments.get("opacity", 1.0),
            "unlit": arguments.get("unlit", True),
        }
        if "height" in arguments:
            params["height"] = arguments["height"]
        result = call_http("/command", {"action": "add_reference_image", "params": params})
    elif name == "blender_apply_texture_material":
        params = {
            "object": arguments.get("object"),
            "path": normalize_input_path(arguments.get("path")),
            "material_name": arguments.get("material_name", "texture material"),
            "roughness": arguments.get("roughness", 0.55),
            "metallic": arguments.get("metallic", 0.0),
            "opacity": arguments.get("opacity", 1.0),
            "texture_scale": arguments.get("texture_scale", [1.0, 1.0]),
            "texture_offset": arguments.get("texture_offset", [0.0, 0.0]),
            "texture_rotation": arguments.get("texture_rotation", 0.0),
            "projection": arguments.get("projection", "uv"),
            "mode": arguments.get("mode", "replace"),
        }
        result = call_http("/command", {"action": "apply_texture_material", "params": params})
    elif name == "blender_apply_material_preset":
        params = {
            "object": arguments.get("object"),
            "preset": arguments.get("preset", "wood_oak"),
            "material_name": arguments.get("material_name", "preset material"),
            "mode": arguments.get("mode", "replace"),
        }
        result = call_http("/command", {"action": "apply_material_preset", "params": params})
    elif name == "blender_create_scene_from_reference":
        result = call_http("/command", {"action": "create_scene_from_reference", "params": arguments})
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
            if payload.get("action") == "import_asset":
                params = payload.setdefault("params", {})
                params["path"] = normalize_input_path(params.get("path"))
            if payload.get("action") == "add_reference_image":
                params = payload.setdefault("params", {})
                params["path"] = normalize_input_path(params.get("path"))
            if payload.get("action") == "apply_texture_material":
                params = payload.setdefault("params", {})
                params["path"] = normalize_input_path(params.get("path"))
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
                "serverInfo": {"name": "codex-blender", "version": "0.14.0"},
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
