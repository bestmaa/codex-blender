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

## Common Workflows

### Inspect And Edit Existing Scenes

Run `inspect_scene` before changing an existing object. Use the exact object name from the response for `transform_object`, `duplicate_object`, `animate_object`, `apply_texture_material`, `apply_material_preset`, or `apply_material_recipe`.

### Reference Image Matching

When the user gives or asks for a reference image workflow:

1. Put the image under `assets/references/`.
2. Add it with `add_reference_image`.
3. Create or import the rough model.
4. Use `setup_reference_camera` or `setup_compare_view`.
5. Render, compare, adjust geometry/materials, and repeat.

Use `create_scene_from_reference` only when there is a structured scene plan; it is an approximation workflow, not automatic perfect image-to-3D conversion.

### Procedural Primitive Workflow

Use `create_primitive` when a scene needs reusable low-level shapes such as beveled boxes, panels, glass panels, cylinders, cones, planes, spheres, or labels. Use it before higher-level furniture/architecture helpers when the requested object is custom but can be built from simple parts.

Use `create_furniture_preset` when the user asks for common room objects such as a shelf, cabinet, desk, bed, door, window, or wall art and does not need a highly custom model.

Use `create_architecture_preset` when the user asks for room or building details such as walls with openings, floor tiles, ceiling panels, stairs, railings, or facade elements.

Use `list_procedural_catalog` when you need to discover available procedural categories, presets, common params, and example files before choosing a creation action.

### Texture Workflow

Put texture files under `assets/textures/`. Use `apply_texture_material` for user-provided images and multi-map materials. Use `texture_scale`, `texture_offset`, `texture_rotation`, and `projection` when the image placement needs tuning. Use `apply_material_preset` for fast built-in materials when no custom image texture is needed. Use `apply_material_recipe` for reusable shader settings plus optional map paths from `assets/material_recipes.json`.

### Import, Fit, And Export

Put importable models under `assets/models/`. Use `import_asset`, then `fit_object_to_bounds` if the imported object is too large, too small, or not aligned to the floor. Use `export_glb` for reusable scene/model exchange and `export_obj` when a simple mesh export is enough.

Use `assets/library.json` as the stable local asset manifest. It records searchable names, types, tags, paths, preview paths, license/source notes, and scale hints for models, textures, and references. Use `search_assets` to find manifest entries by query, type, tag, or extension. Use `import_asset_from_library` when importing a model listed in the manifest.

### Render And Save

Use `set_render_preset` before `render_scene` when speed or quality matters. Use `save_blend` after creating or editing a useful scene.

## MCP Tool Use

MCP tools use the `blender_` prefix, while raw bridge actions use the action names below. Prefer the specific MCP tool when one exists, for example `blender_create_table_model` instead of the generic `blender_command`.

Use `blender_inspect_scene` before transforming, duplicating, texturing, or animating existing objects so object names match Blender exactly.

Use `blender_command` only for newly added actions that do not have a dedicated MCP wrapper yet.

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

Creates an outdoor road scene with road, sidewalks, markings, varied trees, benches, signs, bushes, rocks, street lights, camera, and lighting.

```json
{
  "action": "create_outdoor_scene",
  "params": {
    "road_length": 32,
    "road_width": 5,
    "tree_count": 12,
    "street_light_count": 6,
    "density": 1.0,
    "sidewalk_width": 1.1,
    "bench_count": 4,
    "sign_count": 4,
    "bush_count": 10,
    "rock_count": 8,
    "include_sidewalks": true,
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

### create_primitive

Creates one or more reusable procedural primitives. Supported types include `beveled_box`, `box`, `cylinder`, `cone`, `sphere`, `plane`, `panel`, `glass_panel`, and `label`.

```json
{
  "action": "create_primitive",
  "params": {
    "type": "beveled_box",
    "name": "sample beveled plinth",
    "location": [0, 0, 0.35],
    "dimensions": [2.4, 1.2, 0.7],
    "bevel": 0.08,
    "color": [0.42, 0.50, 0.56, 1],
    "material_name": "soft grey material"
  }
}
```

### create_furniture_preset

Creates one or more procedural furniture presets. Supported presets include `shelf`, `cabinet`, `desk`, `bed`, `door`, `window`, and `wall_art`.

```json
{
  "action": "create_furniture_preset",
  "params": {
    "preset": "shelf",
    "name": "open oak shelf",
    "location": [0, 0, 0],
    "width": 1.4,
    "depth": 0.4,
    "height": 2.2,
    "levels": 5,
    "wood_color": [0.64, 0.42, 0.23, 1],
    "accent_color": [0.26, 0.20, 0.16, 1]
  }
}
```

### create_architecture_preset

Creates one or more procedural architecture presets. Supported presets include `wall_opening`, `floor_tiles`, `ceiling_panels`, `stairs`, `railing`, and `facade`.

```json
{
  "action": "create_architecture_preset",
  "params": {
    "preset": "wall_opening",
    "name": "back wall window opening",
    "location": [0, 2, 0],
    "width": 2.6,
    "depth": 0.12,
    "height": 2.7,
    "opening_width": 1.2,
    "opening_height": 1.15,
    "sill_height": 0.75,
    "wall_color": [0.76, 0.76, 0.72, 1],
    "trim_color": [0.92, 0.90, 0.84, 1]
  }
}
```

### list_procedural_catalog

Lists procedural categories, supported presets, common params, and example files. Use optional `category` to filter to `primitive`, `furniture`, `architecture`, or `outdoor`.

```json
{
  "action": "list_procedural_catalog",
  "params": {}
}
```

### create_chair_model

Creates a reusable modern chair model with a cushion, back, legs, camera, and lighting.

```json
{
  "action": "create_chair_model",
  "params": {
    "width": 1.35,
    "depth": 1.25,
    "height": 2.25,
    "seat_height": 0.95,
    "cushion_thickness": 0.18,
    "wood_color": [0.72, 0.45, 0.25, 1],
    "fabric_color": [0.34, 0.48, 0.56, 1],
    "style": "modern_wood"
  }
}
```

### create_sofa_model

Creates a reusable modern sofa model with cushions, arms, legs, camera, and lighting.

```json
{
  "action": "create_sofa_model",
  "params": {
    "width": 3.2,
    "depth": 1.35,
    "height": 1.55,
    "seat_height": 0.62,
    "cushion_count": 3,
    "cushion_gap": 0.035,
    "fabric_color": [0.42, 0.54, 0.62, 1],
    "leg_color": [0.42, 0.25, 0.14, 1],
    "style": "modern_couch"
  }
}
```

### create_plant_model

Creates a reusable indoor plant model with a pot, stems, broad leaves, camera, and lighting.

```json
{
  "action": "create_plant_model",
  "params": {
    "height": 2.1,
    "pot_radius": 0.42,
    "pot_height": 0.58,
    "leaf_count": 18,
    "stem_count": 5,
    "leaf_color": [0.20, 0.55, 0.34, 1],
    "pot_color": [0.70, 0.62, 0.52, 1],
    "style": "indoor_potted"
  }
}
```

### create_lamp_model

Creates a reusable floor lamp, table lamp, or ceiling panel with visible mesh fixtures and real Blender lights.

```json
{
  "action": "create_lamp_model",
  "params": {
    "lamp_type": "floor",
    "height": 2.4,
    "shade_radius": 0.38,
    "power": 520,
    "metal_color": [0.23, 0.23, 0.22, 1],
    "shade_color": [0.95, 0.86, 0.68, 1],
    "style": "warm_modern"
  }
}
```

### create_furniture_set

Creates a composed furniture scene with a dining table, chairs, rug, plant, floor lamp, camera, and lighting.

```json
{
  "action": "create_furniture_set",
  "params": {
    "table_length": 3.2,
    "table_width": 1.55,
    "chair_count": 4,
    "include_plant": true,
    "include_lamp": true,
    "style": "compact_dining"
  }
}
```

### create_room_layout

Creates a reusable room layout preset. Supported presets are `studio`, `living_room`, `office`, and `gallery`.

```json
{
  "action": "create_room_layout",
  "params": {
    "preset": "living_room",
    "style": "clean_modern"
  }
}
```

### list_assets

Lists local files from `assets/models/`, `assets/textures/`, and `assets/references/`.

```json
{
  "action": "list_assets",
  "params": {
    "type": "texture",
    "extension": "png"
  }
}
```

### search_assets

Searches the stable `assets/library.json` manifest by query, type, tag, and extension.

```json
{
  "action": "search_assets",
  "params": {
    "query": "oak wood",
    "type": "texture",
    "extension": "png",
    "limit": 10
  }
}
```

### import_asset_from_library

Imports a model by library `id`, `name`, or `query`, applies manifest scale hints, and optionally fits it to bounds.

```json
{
  "action": "import_asset_from_library",
  "params": {
    "id": "sample_pyramid_obj",
    "location": [0, 0, 0],
    "fit_to_bounds": true,
    "target_size": [1.5, 1.5, 1.5],
    "target_location": [0, 0, 0],
    "align_to_floor": true
  }
}
```

### fit_object_to_bounds

Scales and places an existing object inside target bounds. Use after `import_asset` when an asset is too large, too small, or not sitting on the floor.

```json
{
  "action": "fit_object_to_bounds",
  "params": {
    "object": "sample_pyramid",
    "target_size": [1.5, 1.5, 1.5],
    "target_location": [0, 0, 0],
    "align_to_floor": true
  }
}
```

### inspect_scene

Returns current scene objects with name, type, transform, dimensions, and material names.

```json
{
  "action": "inspect_scene",
  "params": {
    "include_hidden": false,
    "type": "MESH"
  }
}
```

### transform_object

Moves, rotates, scales, or resizes an existing object. Unspecified transform fields are preserved.

```json
{
  "action": "transform_object",
  "params": {
    "object": "rounded rectangular tabletop",
    "location": [0, 0, 1.75],
    "dimensions": [3.2, 1.7, 0.2]
  }
}
```

### duplicate_object

Duplicates an existing object multiple times with an offset and stable name prefix.

```json
{
  "action": "duplicate_object",
  "params": {
    "object": "front left tapered leg",
    "count": 3,
    "offset": [0.45, 0, 0],
    "name_prefix": "extra table leg"
  }
}
```

### animate_object

Creates simple location, rotation, or scale keyframes for an existing object.

```json
{
  "action": "animate_object",
  "params": {
    "object": "rounded rectangular tabletop",
    "frame_start": 1,
    "frame_end": 80,
    "location_start": [0, 0, 1.55],
    "location_end": [0, 0, 1.9],
    "rotation_start": [0, 0, 0],
    "rotation_end": [0, 0, 0.35]
  }
}
```

### set_render_preset

Applies draft, preview, or final render settings for engine, samples, resolution, and view transform.

```json
{
  "action": "set_render_preset",
  "params": {
    "preset": "preview"
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
    "base_color_path": "assets/textures/wood_basecolor.png",
    "roughness_path": "assets/textures/wood_roughness.png",
    "normal_path": "assets/textures/wood_normal.png",
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

### apply_material_preset

Applies a built-in material preset to an existing Blender object. Available presets: `wood_oak`, `fabric_soft`, `brushed_metal`, `glass_clear`, `matte_plastic`.

```json
{
  "action": "apply_material_preset",
  "params": {
    "object": "darker tabletop underside",
    "preset": "brushed_metal",
    "material_name": "brushed metal underside preset",
    "mode": "replace"
  }
}
```

### apply_material_recipe

Applies a reusable material recipe from `assets/material_recipes.json`. Available recipes: `wood_warm`, `fabric_blue`, `metal_brushed`, `glass_clear`, `plastic_matte`.

```json
{
  "action": "apply_material_recipe",
  "params": {
    "object": "sample_pyramid.001",
    "recipe": "wood_warm",
    "material_name": "warm wood recipe",
    "texture_scale": [1.5, 1.0],
    "projection": "generated",
    "mode": "replace"
  }
}
```

### setup_reference_camera

Sets the active camera to frame a reference/model comparison target.

```json
{
  "action": "setup_reference_camera",
  "params": {
    "reference_object": "table reference image",
    "camera_location": [4.2, -5.4, 2.45],
    "target": [0.0, 0.2, 1.15],
    "lens": 32,
    "resolution": [1280, 720],
    "create_target": true
  }
}
```

### setup_compare_view

Places a reference image plane and camera for side-by-side or background comparison renders.

```json
{
  "action": "setup_compare_view",
  "params": {
    "reference_object": "table reference image",
    "mode": "side_by_side",
    "reference_location": [2.25, 2.15, 1.55],
    "reference_width": 2.5,
    "camera_location": [4.8, -5.8, 2.65],
    "target": [0.55, 0.55, 1.25],
    "lens": 30,
    "resolution": [1280, 720]
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

### export_glb

Exports the current scene or selected objects to a `.glb` file.

```json
{
  "action": "export_glb",
  "params": {
    "output": "exports/modern_table.glb",
    "selected_only": false,
    "include_materials": true
  }
}
```

### export_obj

Exports the current scene or selected objects to an `.obj` file.

```json
{
  "action": "export_obj",
  "params": {
    "output": "exports/modern_table.obj",
    "selected_only": false
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
