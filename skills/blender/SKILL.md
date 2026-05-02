---
name: blender
description: Use this skill when the user wants Codex to control Blender locally, create or edit Blender scenes, import 3D assets, inspect rigs, animate rigged models, assign materials, or render through the Codex Blender bridge.
---

# Blender

Use this skill for Blender automation through the local Codex Blender bridge.

## Assumptions

- Blender is installed on the user's machine.
- The user has installed and enabled `blender_addon/codex_blender_addon.py`.
- The add-on bridge is running at `http://127.0.0.1:8765` unless the user configured another port.

## Workflow

1. Clarify the Blender task only when required details are missing.
2. Prefer the `codex-blender` MCP tools when this plugin is enabled in Codex.
3. Prefer structured JSON commands for supported actions when MCP tools are not available.
4. Use generated Blender Python only when a structured action is not enough.
5. Save reusable command examples under `examples/`.
6. For rigged models, first run `inspect_rig`, then generate animation against the discovered bone names.
7. After add-on code changes, enable `Developer Mode` and use Blender's `Reload Bridge Code` button before testing new actions.

## Safety

The `run_python` action executes arbitrary code inside Blender. Only send code generated in the current trusted workflow, and keep it narrowly scoped.

## Supported Actions

### ping

Checks whether Blender is reachable.

```json
{
  "action": "ping"
}
```

### create_room

Creates a starter room scene with floor, walls, lights, camera, and simple furniture.

```json
{
  "action": "create_room",
  "params": {
    "style": "modern_neon"
  }
}
```

### inspect_rig

Returns armature and bone names for the current Blender scene.

```json
{
  "action": "inspect_rig"
}
```

### create_outdoor_scene

Creates an outdoor road scene with road, trees, street lights, camera, and lighting.

```json
{
  "action": "create_outdoor_scene",
  "params": {
    "road_length": 32,
    "road_width": 5,
    "tree_count": 12,
    "street_light_count": 6,
    "style": "clean_suburban"
  }
}
```

### create_table_model

Creates a reusable modern wooden table model with a rounded tabletop, tapered legs, subtle wood grain, camera, and lighting.

```json
{
  "action": "create_table_model",
  "params": {
    "length": 3.6,
    "width": 2.0,
    "height": 1.55,
    "top_thickness": 0.24,
    "corner_roundness": 0.14,
    "include_grain": true,
    "wood_color": [0.78, 0.47, 0.25, 1],
    "style": "modern_wood"
  }
}
```

### add_reference_image

Adds a local image as a reference plane in the current Blender scene. Use this before or after model creation when matching a generated/reference image.

```json
{
  "action": "add_reference_image",
  "params": {
    "path": "assets/references/modern_table_reference.png",
    "name": "table reference image",
    "location": [0, 2.35, 1.55],
    "rotation": [1.5708, 0, 0],
    "width": 3.2,
    "opacity": 0.85,
    "unlit": true
  }
}
```

### apply_texture_material

Applies a local image as a texture material on an existing Blender object. Use this when the user provides a wood, fabric, stone, label, decal, or pattern image.

```json
{
  "action": "apply_texture_material",
  "params": {
    "object": "rounded rectangular tabletop",
    "path": "assets/textures/wood_basecolor.png",
    "material_name": "wood tabletop texture",
    "roughness": 0.45,
    "metallic": 0.0,
    "opacity": 1.0,
    "texture_scale": [1.0, 1.0],
    "texture_offset": [0.0, 0.0],
    "texture_rotation": 0.0,
    "projection": "uv",
    "mode": "replace"
  }
}
```

### render_scene

Renders the current scene from the active camera to a PNG file.

```json
{
  "action": "render_scene",
  "params": {
    "output": "renders/room.png",
    "resolution": [1280, 720],
    "samples": 32,
    "timeout_seconds": 300
  }
}
```

### save_blend

Saves the current Blender scene to a `.blend` file.

```json
{
  "action": "save_blend",
  "params": {
    "output": "scenes/scene.blend"
  }
}
```

### import_asset

Imports a local 3D asset. Supports `.glb`, `.gltf`, `.fbx`, and `.obj`.

```json
{
  "action": "import_asset",
  "params": {
    "path": "assets/models/sample_pyramid.obj",
    "location": [0, 0, 0],
    "rotation": [0, 0, 0],
    "scale": 1.0
  }
}
```

### create_scene_from_reference

Creates an approximate 3D scene from a structured plan inferred from a reference image.

```json
{
  "action": "create_scene_from_reference",
  "params": {
    "title": "reference scene",
    "objects": [
      {
        "name": "green sofa",
        "shape": "cube",
        "location": [-1.4, 1.2, 0.45],
        "scale": [2.6, 0.85, 0.5],
        "color": [0.08, 0.28, 0.16, 1]
      }
    ]
  }
}
```

### run_python

Runs trusted Blender Python.

```json
{
  "action": "run_python",
  "params": {
    "code": "import bpy\nprint(len(bpy.data.objects))"
  }
}
```
