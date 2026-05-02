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
7. After add-on code changes, use Blender's `Reload Bridge Code` button before testing new actions.

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
