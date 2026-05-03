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
        "name": "blender_create_chair_model",
        "description": "Create a modern chair model with cushion, back, legs, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "width": {"type": "number", "description": "Chair width.", "default": 1.35},
                "depth": {"type": "number", "description": "Chair depth.", "default": 1.25},
                "height": {"type": "number", "description": "Chair total height.", "default": 2.25},
                "seat_height": {"type": "number", "description": "Seat height.", "default": 0.95},
                "cushion_thickness": {"type": "number", "description": "Seat cushion thickness.", "default": 0.18},
                "wood_color": {"type": "array", "items": {"type": "number"}, "default": [0.72, 0.45, 0.25, 1]},
                "fabric_color": {"type": "array", "items": {"type": "number"}, "default": [0.34, 0.48, 0.56, 1]},
                "style": {"type": "string", "description": "Style label.", "default": "modern_wood"},
            }
        ),
    },
    {
        "name": "blender_create_sofa_model",
        "description": "Create a modern sofa model with cushions, arms, legs, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "width": {"type": "number", "description": "Sofa width.", "default": 3.2},
                "depth": {"type": "number", "description": "Sofa depth.", "default": 1.35},
                "height": {"type": "number", "description": "Sofa total height.", "default": 1.55},
                "seat_height": {"type": "number", "description": "Seat height.", "default": 0.62},
                "cushion_count": {"type": "integer", "description": "Number of seat cushions.", "default": 3},
                "cushion_gap": {"type": "number", "description": "Gap between seat cushions.", "default": 0.035},
                "fabric_color": {"type": "array", "items": {"type": "number"}, "default": [0.42, 0.54, 0.62, 1]},
                "leg_color": {"type": "array", "items": {"type": "number"}, "default": [0.42, 0.25, 0.14, 1]},
                "style": {"type": "string", "description": "Style label.", "default": "modern_couch"},
            }
        ),
    },
    {
        "name": "blender_create_plant_model",
        "description": "Create an indoor potted plant model with pot, stems, leaf clusters, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "height": {"type": "number", "description": "Plant total height.", "default": 2.1},
                "pot_radius": {"type": "number", "description": "Pot radius.", "default": 0.42},
                "pot_height": {"type": "number", "description": "Pot height.", "default": 0.58},
                "leaf_count": {"type": "integer", "description": "Number of broad leaves.", "default": 18},
                "stem_count": {"type": "integer", "description": "Number of stems.", "default": 5},
                "leaf_color": {"type": "array", "items": {"type": "number"}, "default": [0.20, 0.55, 0.34, 1]},
                "pot_color": {"type": "array", "items": {"type": "number"}, "default": [0.70, 0.62, 0.52, 1]},
                "style": {"type": "string", "description": "Style label.", "default": "indoor_potted"},
            }
        ),
    },
    {
        "name": "blender_create_lamp_model",
        "description": "Create a reusable floor lamp, table lamp, or ceiling light panel with visible lighting.",
        "inputSchema": json_schema(
            {
                "lamp_type": {"type": "string", "description": "floor, table, or ceiling_panel.", "default": "floor"},
                "height": {"type": "number", "description": "Lamp height.", "default": 2.4},
                "shade_radius": {"type": "number", "description": "Shade or panel radius/size.", "default": 0.38},
                "power": {"type": "number", "description": "Light power.", "default": 520},
                "metal_color": {"type": "array", "items": {"type": "number"}, "default": [0.23, 0.23, 0.22, 1]},
                "shade_color": {"type": "array", "items": {"type": "number"}, "default": [0.95, 0.86, 0.68, 1]},
                "style": {"type": "string", "description": "Style label.", "default": "warm_modern"},
            }
        ),
    },
    {
        "name": "blender_create_furniture_set",
        "description": "Create a composed furniture scene with table, chairs, rug, plant, lamp, camera, and lighting.",
        "inputSchema": json_schema(
            {
                "table_length": {"type": "number", "description": "Dining table length.", "default": 3.2},
                "table_width": {"type": "number", "description": "Dining table width.", "default": 1.55},
                "chair_count": {"type": "integer", "description": "Number of chairs.", "default": 4},
                "include_plant": {"type": "boolean", "description": "Add potted plant.", "default": True},
                "include_lamp": {"type": "boolean", "description": "Add floor lamp.", "default": True},
                "style": {"type": "string", "description": "Style label.", "default": "compact_dining"},
            }
        ),
    },
    {
        "name": "blender_create_room_layout",
        "description": "Create a reusable room layout preset: studio, living_room, office, or gallery.",
        "inputSchema": json_schema(
            {
                "preset": {"type": "string", "description": "studio, living_room, office, or gallery.", "default": "living_room"},
                "style": {"type": "string", "description": "Style label.", "default": "clean_modern"},
            }
        ),
    },
    {
        "name": "blender_list_assets",
        "description": "List local assets from assets/models, assets/textures, and assets/references.",
        "inputSchema": json_schema(
            {
                "type": {"type": "string", "description": "Optional asset type: model, texture, or reference."},
                "extension": {"type": "string", "description": "Optional extension filter, for example obj or png."},
            }
        ),
    },
    {
        "name": "blender_fit_object_to_bounds",
        "description": "Scale and place an object inside target bounds, optionally aligning its bottom to the floor.",
        "inputSchema": json_schema(
            {
                "object": {"type": "string", "description": "Object name to fit."},
                "target_size": {"description": "Target size as a number or [x, y, z].", "default": [1, 1, 1]},
                "target_location": {"type": "array", "items": {"type": "number"}, "default": [0, 0, 0]},
                "align_to_floor": {"type": "boolean", "description": "Align object bottom to target_location z.", "default": True},
            },
            required=["object"],
        ),
    },
    {
        "name": "blender_inspect_scene",
        "description": "Inspect current scene objects with names, types, transforms, dimensions, and materials.",
        "inputSchema": json_schema(
            {
                "include_hidden": {"type": "boolean", "description": "Include hidden objects.", "default": False},
                "type": {"type": "string", "description": "Optional Blender object type filter, for example MESH or LIGHT."},
            }
        ),
    },
    {
        "name": "blender_transform_object",
        "description": "Move, rotate, scale, or resize an existing object while preserving unspecified transforms.",
        "inputSchema": json_schema(
            {
                "object": {"type": "string", "description": "Object name to transform."},
                "location": {"type": "array", "items": {"type": "number"}, "description": "Optional location [x, y, z]."},
                "rotation": {"type": "array", "items": {"type": "number"}, "description": "Optional Euler rotation [x, y, z]."},
                "scale": {"description": "Optional scale as a number or [x, y, z]."},
                "dimensions": {"type": "array", "items": {"type": "number"}, "description": "Optional target dimensions [x, y, z]."},
            },
            required=["object"],
        ),
    },
    {
        "name": "blender_duplicate_object",
        "description": "Duplicate an existing object multiple times with an offset and stable name prefix.",
        "inputSchema": json_schema(
            {
                "object": {"type": "string", "description": "Object name to duplicate."},
                "count": {"type": "integer", "description": "Number of duplicates to create.", "default": 3},
                "offset": {"type": "array", "items": {"type": "number"}, "default": [1, 0, 0]},
                "name_prefix": {"type": "string", "description": "Prefix for duplicate object names.", "default": "duplicate"},
            },
            required=["object"],
        ),
    },
    {
        "name": "blender_animate_object",
        "description": "Create simple location, rotation, and scale keyframes for an object.",
        "inputSchema": json_schema(
            {
                "object": {"type": "string", "description": "Object name to animate."},
                "frame_start": {"type": "integer", "description": "Start frame.", "default": 1},
                "frame_end": {"type": "integer", "description": "End frame.", "default": 80},
                "location_start": {"type": "array", "items": {"type": "number"}},
                "location_end": {"type": "array", "items": {"type": "number"}},
                "rotation_start": {"type": "array", "items": {"type": "number"}},
                "rotation_end": {"type": "array", "items": {"type": "number"}},
                "scale_start": {"type": "array", "items": {"type": "number"}},
                "scale_end": {"type": "array", "items": {"type": "number"}},
            },
            required=["object"],
        ),
    },
    {
        "name": "blender_set_render_preset",
        "description": "Apply draft, preview, or final render settings for engine, samples, resolution, and view transform.",
        "inputSchema": json_schema(
            {
                "preset": {"type": "string", "description": "draft, preview, or final.", "default": "preview"},
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
        "name": "blender_export_glb",
        "description": "Export the current Blender scene or selected objects to a .glb file.",
        "inputSchema": json_schema(
            {
                "output": {
                    "type": "string",
                    "description": "Output .glb path, relative to the plugin folder or absolute.",
                    "default": "exports/scene.glb",
                },
                "selected_only": {
                    "type": "boolean",
                    "description": "Export only selected objects.",
                    "default": False,
                },
                "include_materials": {
                    "type": "boolean",
                    "description": "Include materials in the exported GLB.",
                    "default": True,
                },
            }
        ),
    },
    {
        "name": "blender_export_obj",
        "description": "Export the current Blender scene or selected objects to an .obj file.",
        "inputSchema": json_schema(
            {
                "output": {
                    "type": "string",
                    "description": "Output .obj path, relative to the plugin folder or absolute.",
                    "default": "exports/scene.obj",
                },
                "selected_only": {
                    "type": "boolean",
                    "description": "Export only selected objects.",
                    "default": False,
                },
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
                    "description": "Texture image path alias for base_color_path, such as assets/textures/wood.png.",
                },
                "base_color_path": {
                    "type": "string",
                    "description": "Base color texture image path.",
                },
                "roughness_path": {
                    "type": "string",
                    "description": "Optional roughness texture image path.",
                },
                "normal_path": {
                    "type": "string",
                    "description": "Optional normal map texture image path.",
                },
                "metallic_path": {
                    "type": "string",
                    "description": "Optional metallic texture image path.",
                },
                "alpha_path": {
                    "type": "string",
                    "description": "Optional alpha texture image path.",
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
            required=["object"],
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
        "name": "blender_setup_reference_camera",
        "description": "Set the active camera to frame a reference/model comparison target.",
        "inputSchema": json_schema(
            {
                "reference_object": {
                    "type": "string",
                    "description": "Optional reference plane object name to validate.",
                    "default": "table reference image",
                },
                "camera_location": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Camera location as [x, y, z].",
                    "default": [4.2, -5.4, 2.45],
                },
                "target": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Camera look-at target as [x, y, z].",
                    "default": [0, 0, 1.1],
                },
                "lens": {
                    "type": "number",
                    "description": "Camera lens in millimeters.",
                    "default": 35,
                },
                "resolution": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional render resolution as [width, height].",
                    "default": [1280, 720],
                },
                "create_target": {
                    "type": "boolean",
                    "description": "Create a visible empty at the look-at target.",
                    "default": True,
                },
            }
        ),
    },
    {
        "name": "blender_setup_compare_view",
        "description": "Place a reference image plane and camera for side-by-side or background comparison renders.",
        "inputSchema": json_schema(
            {
                "reference_object": {
                    "type": "string",
                    "description": "Reference plane object name.",
                    "default": "table reference image",
                },
                "mode": {
                    "type": "string",
                    "description": "Compare mode: side_by_side or background.",
                    "default": "side_by_side",
                },
                "reference_location": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Reference plane location.",
                    "default": [2.25, 2.15, 1.55],
                },
                "reference_width": {
                    "type": "number",
                    "description": "Reference plane width.",
                    "default": 2.5,
                },
                "camera_location": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Camera location.",
                    "default": [4.8, -5.8, 2.65],
                },
                "target": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 3,
                    "maxItems": 3,
                    "description": "Camera look-at target.",
                    "default": [0.55, 0.55, 1.25],
                },
                "lens": {
                    "type": "number",
                    "description": "Camera lens in millimeters.",
                    "default": 30,
                },
                "resolution": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional render resolution.",
                    "default": [1280, 720],
                },
            }
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
    elif name == "blender_create_chair_model":
        params = {
            "width": arguments.get("width", 1.35),
            "depth": arguments.get("depth", 1.25),
            "height": arguments.get("height", 2.25),
            "seat_height": arguments.get("seat_height", 0.95),
            "cushion_thickness": arguments.get("cushion_thickness", 0.18),
            "wood_color": arguments.get("wood_color", [0.72, 0.45, 0.25, 1]),
            "fabric_color": arguments.get("fabric_color", [0.34, 0.48, 0.56, 1]),
            "style": arguments.get("style", "modern_wood"),
        }
        result = call_http("/command", {"action": "create_chair_model", "params": params})
    elif name == "blender_create_sofa_model":
        params = {
            "width": arguments.get("width", 3.2),
            "depth": arguments.get("depth", 1.35),
            "height": arguments.get("height", 1.55),
            "seat_height": arguments.get("seat_height", 0.62),
            "cushion_count": arguments.get("cushion_count", 3),
            "cushion_gap": arguments.get("cushion_gap", 0.035),
            "fabric_color": arguments.get("fabric_color", [0.42, 0.54, 0.62, 1]),
            "leg_color": arguments.get("leg_color", [0.42, 0.25, 0.14, 1]),
            "style": arguments.get("style", "modern_couch"),
        }
        result = call_http("/command", {"action": "create_sofa_model", "params": params})
    elif name == "blender_create_plant_model":
        params = {
            "height": arguments.get("height", 2.1),
            "pot_radius": arguments.get("pot_radius", 0.42),
            "pot_height": arguments.get("pot_height", 0.58),
            "leaf_count": arguments.get("leaf_count", 18),
            "stem_count": arguments.get("stem_count", 5),
            "leaf_color": arguments.get("leaf_color", [0.20, 0.55, 0.34, 1]),
            "pot_color": arguments.get("pot_color", [0.70, 0.62, 0.52, 1]),
            "style": arguments.get("style", "indoor_potted"),
        }
        result = call_http("/command", {"action": "create_plant_model", "params": params})
    elif name == "blender_create_lamp_model":
        params = {
            "lamp_type": arguments.get("lamp_type", "floor"),
            "height": arguments.get("height", 2.4),
            "shade_radius": arguments.get("shade_radius", 0.38),
            "power": arguments.get("power", 520),
            "metal_color": arguments.get("metal_color", [0.23, 0.23, 0.22, 1]),
            "shade_color": arguments.get("shade_color", [0.95, 0.86, 0.68, 1]),
            "style": arguments.get("style", "warm_modern"),
        }
        result = call_http("/command", {"action": "create_lamp_model", "params": params})
    elif name == "blender_create_furniture_set":
        params = {
            "table_length": arguments.get("table_length", 3.2),
            "table_width": arguments.get("table_width", 1.55),
            "chair_count": arguments.get("chair_count", 4),
            "include_plant": arguments.get("include_plant", True),
            "include_lamp": arguments.get("include_lamp", True),
            "style": arguments.get("style", "compact_dining"),
        }
        result = call_http("/command", {"action": "create_furniture_set", "params": params})
    elif name == "blender_create_room_layout":
        params = {
            "preset": arguments.get("preset", "living_room"),
            "style": arguments.get("style", "clean_modern"),
        }
        result = call_http("/command", {"action": "create_room_layout", "params": params})
    elif name == "blender_list_assets":
        params = {
            "type": arguments.get("type"),
            "extension": arguments.get("extension"),
        }
        result = call_http("/command", {"action": "list_assets", "params": params})
    elif name == "blender_fit_object_to_bounds":
        params = {
            "object": arguments.get("object"),
            "target_size": arguments.get("target_size", [1, 1, 1]),
            "target_location": arguments.get("target_location", [0, 0, 0]),
            "align_to_floor": arguments.get("align_to_floor", True),
        }
        result = call_http("/command", {"action": "fit_object_to_bounds", "params": params})
    elif name == "blender_inspect_scene":
        params = {
            "include_hidden": arguments.get("include_hidden", False),
            "type": arguments.get("type"),
        }
        result = call_http("/command", {"action": "inspect_scene", "params": params})
    elif name == "blender_transform_object":
        params = {"object": arguments.get("object")}
        for key in ("location", "rotation", "scale", "dimensions"):
            if key in arguments:
                params[key] = arguments[key]
        result = call_http("/command", {"action": "transform_object", "params": params})
    elif name == "blender_duplicate_object":
        params = {
            "object": arguments.get("object"),
            "count": arguments.get("count", 3),
            "offset": arguments.get("offset", [1, 0, 0]),
            "name_prefix": arguments.get("name_prefix", "duplicate"),
        }
        result = call_http("/command", {"action": "duplicate_object", "params": params})
    elif name == "blender_animate_object":
        params = {
            "object": arguments.get("object"),
            "frame_start": arguments.get("frame_start", 1),
            "frame_end": arguments.get("frame_end", 80),
        }
        for key in (
            "location_start",
            "location_end",
            "rotation_start",
            "rotation_end",
            "scale_start",
            "scale_end",
        ):
            if key in arguments:
                params[key] = arguments[key]
        result = call_http("/command", {"action": "animate_object", "params": params})
    elif name == "blender_set_render_preset":
        params = {"preset": arguments.get("preset", "preview")}
        result = call_http("/command", {"action": "set_render_preset", "params": params})
    elif name == "blender_save_blend":
        params = {"output": normalize_output_path(arguments.get("output", "scenes/scene.blend"))}
        result = call_http("/command", {"action": "save_blend", "params": params})
    elif name == "blender_export_glb":
        params = {
            "output": normalize_output_path(arguments.get("output", "exports/scene.glb")),
            "selected_only": arguments.get("selected_only", False),
            "include_materials": arguments.get("include_materials", True),
        }
        result = call_http("/command", {"action": "export_glb", "params": params})
    elif name == "blender_export_obj":
        params = {
            "output": normalize_output_path(arguments.get("output", "exports/scene.obj")),
            "selected_only": arguments.get("selected_only", False),
        }
        result = call_http("/command", {"action": "export_obj", "params": params})
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
            "base_color_path": normalize_input_path(arguments.get("base_color_path")),
            "roughness_path": normalize_input_path(arguments.get("roughness_path")),
            "normal_path": normalize_input_path(arguments.get("normal_path")),
            "metallic_path": normalize_input_path(arguments.get("metallic_path")),
            "alpha_path": normalize_input_path(arguments.get("alpha_path")),
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
    elif name == "blender_setup_reference_camera":
        params = {
            "reference_object": arguments.get("reference_object", "table reference image"),
            "camera_location": arguments.get("camera_location", [4.2, -5.4, 2.45]),
            "target": arguments.get("target", [0, 0, 1.1]),
            "lens": arguments.get("lens", 35),
            "resolution": arguments.get("resolution", [1280, 720]),
            "create_target": arguments.get("create_target", True),
        }
        result = call_http("/command", {"action": "setup_reference_camera", "params": params})
    elif name == "blender_setup_compare_view":
        params = {
            "reference_object": arguments.get("reference_object", "table reference image"),
            "mode": arguments.get("mode", "side_by_side"),
            "reference_location": arguments.get("reference_location", [2.25, 2.15, 1.55]),
            "reference_width": arguments.get("reference_width", 2.5),
            "camera_location": arguments.get("camera_location", [4.8, -5.8, 2.65]),
            "target": arguments.get("target", [0.55, 0.55, 1.25]),
            "lens": arguments.get("lens", 30),
            "resolution": arguments.get("resolution", [1280, 720]),
        }
        result = call_http("/command", {"action": "setup_compare_view", "params": params})
    elif name == "blender_create_scene_from_reference":
        result = call_http("/command", {"action": "create_scene_from_reference", "params": arguments})
    elif name == "blender_inspect_rig":
        result = call_http("/command", {"action": "inspect_rig"})
    elif name == "blender_command":
        payload = arguments.get("payload")
        if not isinstance(payload, dict):
            result = {"ok": False, "error": "payload must be an object"}
        else:
            if payload.get("action") in {"render_scene", "save_blend", "export_glb", "export_obj"}:
                params = payload.setdefault("params", {})
                default_output = "scenes/scene.blend" if payload.get("action") == "save_blend" else "exports/scene.glb" if payload.get("action") == "export_glb" else "exports/scene.obj" if payload.get("action") == "export_obj" else "renders/room.png"
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
                for texture_key in ("base_color_path", "roughness_path", "normal_path", "metallic_path", "alpha_path"):
                    params[texture_key] = normalize_input_path(params.get(texture_key))
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
                "serverInfo": {"name": "codex-blender", "version": "0.97.0"},
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
