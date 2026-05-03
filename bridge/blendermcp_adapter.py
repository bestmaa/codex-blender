"""Translate common BlenderMCP-style payloads to native Codex Blender commands."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PRIMITIVE_TYPES = {"cube", "sphere", "cylinder", "cone"}


def compatibility_error(message: str, *, command: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "error": message,
        "errorType": "UnsupportedCompatibilityPayload",
        "hint": "Use a native Codex Blender action or one of the documented BlenderMCP compatibility commands.",
    }
    if command:
        result["command"] = command
    return result


def get_command_name(payload: dict[str, Any]) -> str | None:
    value = payload.get("tool") or payload.get("name") or payload.get("command")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def get_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("params", "arguments", "args"):
        value = payload.get(key)
        if isinstance(value, dict):
            return deepcopy(value)
    return {}


def first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def translate_create_object(command: str, args: dict[str, Any]) -> dict[str, Any]:
    primitive_type = first_string(args.get("type"), args.get("object_type"), args.get("primitive"))
    if primitive_type is None:
        return compatibility_error("create_object requires a primitive type.", command=command)
    primitive_type = primitive_type.lower()
    if primitive_type not in PRIMITIVE_TYPES:
        return compatibility_error(
            f"create_object primitive type is not supported yet: {primitive_type}",
            command=command,
        )

    name = first_string(args.get("name"), args.get("object_name")) or f"compatibility {primitive_type}"
    obj: dict[str, Any] = {
        "name": name,
        "shape": primitive_type,
        "location": args.get("location", [0, 0, 0]),
        "rotation": args.get("rotation", [0, 0, 0]),
        "scale": args.get("dimensions", args.get("scale", [1, 1, 1])),
        "color": args.get("color", args.get("base_color", [0.8, 0.8, 0.8, 1])),
        "material": args.get("material", f"{name} material"),
    }
    for key in ("radius", "depth", "radius1", "radius2"):
        if key in args:
            obj[key] = args[key]

    return {
        "action": "create_scene_from_reference",
        "params": {
            "title": f"BlenderMCP compatibility {primitive_type}",
            "objects": [obj],
        },
    }


def translate_apply_material(command: str, args: dict[str, Any]) -> dict[str, Any]:
    object_name = first_string(args.get("object"), args.get("object_name"), args.get("name"))
    if object_name is None:
        return compatibility_error("apply_material requires an object name.", command=command)

    if any(key in args for key in ("path", "base_color_path", "texture_path")):
        params = {
            "object": object_name,
            "path": args.get("path", args.get("texture_path")),
            "base_color_path": args.get("base_color_path"),
            "roughness_path": args.get("roughness_path"),
            "normal_path": args.get("normal_path"),
            "metallic_path": args.get("metallic_path"),
            "alpha_path": args.get("alpha_path"),
            "material_name": args.get("material_name", args.get("material", "compatibility texture material")),
            "roughness": args.get("roughness", 0.55),
            "metallic": args.get("metallic", 0.0),
            "opacity": args.get("opacity", 1.0),
            "texture_scale": args.get("texture_scale", [1.0, 1.0]),
            "texture_offset": args.get("texture_offset", [0.0, 0.0]),
            "texture_rotation": args.get("texture_rotation", 0.0),
            "projection": args.get("projection", "uv"),
            "mode": args.get("mode", "replace"),
        }
        return {"action": "apply_texture_material", "params": params}

    preset = first_string(args.get("preset"), args.get("material_preset"))
    if preset:
        return {
            "action": "apply_material_preset",
            "params": {
                "object": object_name,
                "preset": preset,
                "material_name": args.get("material_name", args.get("material", f"{object_name} {preset}")),
                "mode": args.get("mode", "replace"),
            },
        }

    return compatibility_error(
        "apply_material requires a supported preset or texture path.",
        command=command,
    )


def translate_blendermcp_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a native bridge payload, or an error result for unsupported compatibility payloads."""

    if not isinstance(payload, dict):
        return compatibility_error("Compatibility payload must be a JSON object.")
    if isinstance(payload.get("action"), str):
        return deepcopy(payload)

    command = get_command_name(payload)
    if command is None:
        return compatibility_error("Compatibility payload requires tool, name, command, or action.")
    normalized = command.lower().replace("-", "_")
    args = get_arguments(payload)

    if normalized in {"ping", "health", "blender_health"}:
        return {"action": "ping", "params": {}}
    if normalized in {"get_scene_info", "blender_scene_get_info", "scene_info"}:
        return {
            "action": "inspect_scene",
            "params": {
                "include_hidden": args.get("include_hidden", False),
                **({"type": args["type"]} if "type" in args else {}),
            },
        }
    if normalized in {"get_object_info", "blender_object_get_info", "object_info"}:
        return {
            "action": "inspect_scene",
            "params": {
                "include_hidden": True,
                **({"type": args["type"]} if "type" in args else {}),
            },
        }
    if normalized in {"create_object", "blender_object_create"}:
        return translate_create_object(normalized, args)
    if normalized in {"modify_object", "blender_object_modify"}:
        object_name = first_string(args.get("object"), args.get("object_name"), args.get("name"))
        if object_name is None:
            return compatibility_error("modify_object requires an object name.", command=normalized)
        params = {"object": object_name}
        for key in ("location", "rotation", "scale", "dimensions"):
            if key in args:
                params[key] = args[key]
        return {"action": "transform_object", "params": params}
    if normalized in {"apply_material", "blender_material_apply"}:
        return translate_apply_material(normalized, args)
    if normalized in {"render", "render_scene", "blender_render"}:
        return {
            "action": "render_scene",
            "params": {
                "output": args.get("output", args.get("filepath", "renders/compatibility.png")),
                "resolution": args.get("resolution", [1280, 720]),
                "samples": args.get("samples", 32),
                **({"timeout_seconds": args["timeout_seconds"]} if "timeout_seconds" in args else {}),
            },
        }
    if normalized in {"save_scene", "save_blend", "blender_save"}:
        return {"action": "save_blend", "params": {"output": args.get("output", args.get("filepath", "scenes/compatibility.blend"))}}
    if normalized in {"import_asset", "import_model", "blender_import_asset"}:
        return {
            "action": "import_asset",
            "params": {
                "path": args.get("path", args.get("filepath")),
                "location": args.get("location", [0, 0, 0]),
                "rotation": args.get("rotation", [0, 0, 0]),
                "scale": args.get("scale", 1.0),
            },
        }
    if normalized == "export_glb":
        return {
            "action": "export_glb",
            "params": {
                "output": args.get("output", args.get("filepath", "exports/compatibility.glb")),
                "selected_only": args.get("selected_only", False),
                "include_materials": args.get("include_materials", True),
            },
        }
    if normalized == "export_obj":
        return {
            "action": "export_obj",
            "params": {
                "output": args.get("output", args.get("filepath", "exports/compatibility.obj")),
                "selected_only": args.get("selected_only", False),
            },
        }
    if normalized in {"execute_blender_code", "run_python"}:
        code = args.get("code")
        if not isinstance(code, str) or not code.strip():
            return compatibility_error("execute_blender_code requires non-empty code.", command=normalized)
        return {"action": "run_python", "params": {"code": code}}

    return compatibility_error(f"Unsupported BlenderMCP compatibility command: {command}", command=normalized)
