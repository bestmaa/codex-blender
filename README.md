# Codex Blender

Codex Blender is an open-source local bridge for controlling Blender from Codex or a terminal command. It runs a small HTTP server inside Blender, then accepts structured JSON commands for scene creation, asset import, rendering, saving, and inspection.

This is not a cloud connector. Blender runs locally on your machine.

## What It Can And Cannot Do

Codex Blender can create procedural scenes, import local assets, apply materials and textures, place reference images, render, save, export, inspect objects, and perform simple transforms or animations through structured commands.

It cannot turn any arbitrary image into a perfect production 3D model by itself. Image-to-model work is an iterative workflow: add a reference, create or import a base model, adjust geometry/materials/camera, render, compare, and repeat.

## Features

- Start and stop a local Blender bridge at `http://127.0.0.1:8765`.
- Create a starter room scene.
- Create an outdoor road scene with trees and street lights.
- Create a reusable modern wooden table model.
- Create a reusable modern chair model.
- Create a reusable modern sofa model.
- Create a reusable indoor plant model.
- Create reusable floor, table, and ceiling lamp models with real Blender lights.
- Create reusable procedural primitives such as beveled boxes, panels, glass panels, cylinders, cones, planes, spheres, and labels.
- Create procedural furniture presets such as shelves, cabinets, desks, beds, doors, windows, and wall art.
- Create procedural architecture presets such as walls with openings, floor tiles, ceiling panels, stairs, railings, and facades.
- Create a composed furniture set scene.
- Create reusable room layout presets.
- List local model, texture, and reference assets.
- Fit and place imported assets inside target bounds.
- Inspect current scene objects before editing.
- Move, rotate, scale, and resize named scene objects.
- Duplicate and arrange repeated objects.
- Add simple object keyframe animations.
- Apply draft, preview, and final render presets.
- Add reference images as textured planes for side-by-side modeling.
- Apply user-provided image textures to Blender objects.
- Create approximate scenes from structured reference-image plans.
- Import local `.glb`, `.gltf`, `.fbx`, and `.obj` assets.
- Export scenes/models to `.glb` and `.obj`.
- Render the current scene to PNG.
- Save the current scene to `.blend`.
- Inspect armatures and bone names.
- Use a development-only reload button to refresh add-on code without reinstalling.

## Requirements

- Blender 3.6 or newer.
- Python available from your terminal.
- Codex is optional. The bridge can be used directly from a terminal.

## Project Layout

```text
codex-blender/
  .codex-plugin/plugin.json
  .mcp.json
  blender_addon/codex_blender_addon.py
  bridge/codex_blender_bridge.py
  scripts/codex_blender_mcp.py
  skills/blender/SKILL.md
  examples/
  assets/models/
  renders/
  scenes/
```

Use these folders by convention:

```text
  assets/models/  3D input assets
  exports/        generated model exports
  renders/        generated PNG renders
  scenes/         generated .blend files
```

`exports/`, `renders/`, and `scenes/` are ignored by Git.

Stable JSON commands live directly under `examples/` and are covered by `scripts/validate_project.py`. One-off local experiments can be kept in `examples/dev/`, which is ignored by Git except for its README.

Stable reference images used by examples or docs live directly under `assets/references/`. One-off visual references can be kept in `assets/references/dev/`, which is ignored by Git except for its README.

## Install The Blender Add-On

### From Source

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons > Install`.
3. Select:

```text
blender_addon/codex_blender_addon.py
```

4. Enable `Codex Blender Bridge`.
5. In the 3D Viewport, press `N` to open the sidebar.
6. Open the `Codex` tab.
7. Click `Start Bridge`.

### From ZIP

Download the latest add-on ZIP from GitHub Releases:

```text
https://github.com/bestmaa/codex-blender/releases
```

Download the current versioned ZIP, for example:

```text
codex_blender_addon_v1.2.2.zip
```

Or build it locally:

Build an installable ZIP:

```powershell
python scripts\package_addon.py
```

Then install the generated ZIP from `dist/` in Blender:

```text
Edit > Preferences > Add-ons > Install
```

Check that the bridge is running:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
```

Expected response:

```json
{
  "ok": true,
  "message": "Codex Blender Bridge is healthy."
}
```

## First Run

1. Install and enable the Blender add-on.
2. Click `Start Bridge` in Blender's `Codex` sidebar tab.
3. Open a terminal in this project folder.
4. Run a health check.
5. Run one scene command.
6. Render or save the result.

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
python bridge\codex_blender_bridge.py examples\create_room.json
python bridge\codex_blender_bridge.py examples\render_scene.json
```

## Use From Terminal

Run commands from the project folder.

For a complete smoke test, see:

```text
docs/quickstart-demo.md
```

When Blender is running, selected examples can also be tested with:

```powershell
python scripts\smoke_test_bridge.py
python scripts\smoke_test_blendermcp.py
```

For image/reference matching, see:

```text
docs/reference-workflow.md
```

For the stable JSON command schema, see:

```text
docs/commands.md
```

For MCP tool coverage and raw-command notes, see:

```text
docs/mcp-tools.md
```

For BlenderMCP compatibility planning, see:

```text
docs/blendermcp-compatibility.md
```

For common local setup and runtime issues, see:

```text
docs/troubleshooting.md
```

For Windows, WSL, UNC, and PowerShell path rules, see:

```text
docs/windows-paths.md
```

## Common Commands

```powershell
python bridge\codex_blender_bridge.py examples\create_table_model.json
python bridge\codex_blender_bridge.py examples\create_primitive_library.json
python bridge\codex_blender_bridge.py examples\create_furniture_presets.json
python bridge\codex_blender_bridge.py examples\create_architecture_presets.json
python bridge\codex_blender_bridge.py examples\create_furniture_set.json
python bridge\codex_blender_bridge.py examples\add_reference_image.json
python bridge\codex_blender_bridge.py examples\setup_compare_view.json
python bridge\codex_blender_bridge.py examples\set_render_preset.json
python bridge\codex_blender_bridge.py examples\render_scene.json
python bridge\codex_blender_bridge.py examples\save_blend.json
```

For release ZIP packaging, see:

```text
docs/release-packaging.md
```

For included demo assets, see:

```text
docs/demo-assets.md
```

For beta release notes, see:

```text
docs/beta-release-notes.md
```

For draft v1 release notes, see:

```text
docs/release-notes-v1.md
```

For practical limitations and expectations, see:

```text
docs/known-limitations.md
```

For the final smoke test matrix, see:

```text
docs/smoke-test-matrix.md
```

For the final new-user walkthrough, see:

```text
docs/final-user-walkthrough.md
```

For Windows path and PowerShell quoting examples, see:

```text
docs/windows-paths.md
```

Create a starter room:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
```

Create an outdoor road scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_outdoor_scene.json
```

Create a modern table model:

```powershell
python bridge\codex_blender_bridge.py examples\create_table_model.json
```

Create a procedural primitive sample scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_primitive_library.json
```

Create procedural furniture presets:

```powershell
python bridge\codex_blender_bridge.py examples\create_furniture_presets.json
```

Create procedural architecture presets:

```powershell
python bridge\codex_blender_bridge.py examples\create_architecture_presets.json
```

Create a modern chair model:

```powershell
python bridge\codex_blender_bridge.py examples\create_chair_model.json
```

Create a modern sofa model:

```powershell
python bridge\codex_blender_bridge.py examples\create_sofa_model.json
```

Create an indoor plant model:

```powershell
python bridge\codex_blender_bridge.py examples\create_plant_model.json
```

Create a lamp model:

```powershell
python bridge\codex_blender_bridge.py examples\create_lamp_model.json
```

Create a furniture set scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_furniture_set.json
```

Create a room layout preset:

```powershell
python bridge\codex_blender_bridge.py examples\create_room_layout.json
```

List local assets:

```powershell
python bridge\codex_blender_bridge.py examples\list_assets.json
```

Fit the sample imported asset:

```powershell
python bridge\codex_blender_bridge.py examples\fit_sample_asset.json
```

Inspect the current scene:

```powershell
python bridge\codex_blender_bridge.py examples\inspect_scene.json
```

Transform the table top:

```powershell
python bridge\codex_blender_bridge.py examples\transform_tabletop.json
```

Duplicate a table leg:

```powershell
python bridge\codex_blender_bridge.py examples\duplicate_table_leg.json
```

Animate the table top:

```powershell
python bridge\codex_blender_bridge.py examples\animate_tabletop.json
```

Apply a render preset:

```powershell
python bridge\codex_blender_bridge.py examples\set_render_preset.json
```

Add a reference image plane:

```powershell
python bridge\codex_blender_bridge.py examples\add_reference_image.json
```

Apply an image texture to an object:

```powershell
python bridge\codex_blender_bridge.py examples\apply_table_texture.json
```

Apply a scaled image texture to an object:

```powershell
python bridge\codex_blender_bridge.py examples\apply_scaled_wood_texture.json
```

Apply a multi-map texture material:

```powershell
python bridge\codex_blender_bridge.py examples\apply_multimap_wood_texture.json
```

Apply a built-in material preset:

```powershell
python bridge\codex_blender_bridge.py examples\apply_material_preset.json
```

Set up a reference camera:

```powershell
python bridge\codex_blender_bridge.py examples\setup_reference_camera.json
```

Set up a side-by-side compare view:

```powershell
python bridge\codex_blender_bridge.py examples\setup_compare_view.json
```

Export the current scene to GLB:

```powershell
python bridge\codex_blender_bridge.py examples\export_table_glb.json
```

Export the current scene to OBJ:

```powershell
python bridge\codex_blender_bridge.py examples\export_table_obj.json
```

Import a local asset:

```powershell
python bridge\codex_blender_bridge.py examples\import_asset.json
```

Render the current scene:

```powershell
python bridge\codex_blender_bridge.py examples\render_scene.json
```

Save the current scene:

```powershell
python bridge\codex_blender_bridge.py examples\save_blend.json
```

Inspect rigs:

```powershell
python bridge\codex_blender_bridge.py examples\inspect_rig.json
```

## Validate The Project

Run local checks without launching Blender:

```powershell
python scripts\validate_project.py
```

## Example Commands

Create room:

```json
{
  "action": "create_room",
  "params": {
    "style": "modern_neon"
  }
}
```

Create outdoor scene:

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

Create table model:

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

Create chair model:

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

Create sofa model:

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

Create plant model:

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

Create lamp model:

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

Create furniture set:

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

Create room layout:

```json
{
  "action": "create_room_layout",
  "params": {
    "preset": "living_room",
    "style": "clean_modern"
  }
}
```

List assets:

```json
{
  "action": "list_assets",
  "params": {
    "type": "texture",
    "extension": "png"
  }
}
```

Fit object to bounds:

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

Inspect scene:

```json
{
  "action": "inspect_scene",
  "params": {
    "include_hidden": false,
    "type": "MESH"
  }
}
```

Transform object:

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

Duplicate object:

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

Animate object:

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

Set render preset:

```json
{
  "action": "set_render_preset",
  "params": {
    "preset": "preview"
  }
}
```

Add reference image:

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

Apply texture material:

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

Apply material preset:

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

Set up reference camera:

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

Set up compare view:

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

Export GLB:

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

Export OBJ:

```json
{
  "action": "export_obj",
  "params": {
    "output": "exports/modern_table.obj",
    "selected_only": false
  }
}
```

Import asset:

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

Render scene:

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

Save scene:

```json
{
  "action": "save_blend",
  "params": {
    "output": "scenes/scene.blend"
  }
}
```

## Supported Actions

Supported v1.2.2 actions:

- `ping`
- `create_room`
- `create_outdoor_scene`
- `create_table_model`
- `create_primitive`
- `create_furniture_preset`
- `create_architecture_preset`
- `create_chair_model`
- `create_sofa_model`
- `create_plant_model`
- `create_lamp_model`
- `create_furniture_set`
- `create_room_layout`
- `list_assets`
- `fit_object_to_bounds`
- `inspect_scene`
- `transform_object`
- `duplicate_object`
- `animate_object`
- `set_render_preset`
- `add_reference_image`
- `apply_texture_material`
- `apply_material_preset`
- `setup_reference_camera`
- `setup_compare_view`
- `export_glb`
- `export_obj`
- `create_scene_from_reference`
- `import_asset`
- `render_scene`
- `save_blend`
- `inspect_rig`
- `run_python`

`run_python` executes arbitrary Python inside Blender. Use it only with trusted local commands.

## Codex Skill And MCP

This repository includes:

```text
skills/blender/SKILL.md
scripts/codex_blender_mcp.py
.mcp.json
```

When connected as a Codex plugin/MCP server, it exposes:

- `blender_health`
- `blender_create_room`
- `blender_create_outdoor_scene`
- `blender_create_table_model`
- `blender_create_primitive`
- `blender_create_furniture_preset`
- `blender_create_architecture_preset`
- `blender_create_chair_model`
- `blender_create_sofa_model`
- `blender_create_plant_model`
- `blender_create_lamp_model`
- `blender_create_furniture_set`
- `blender_create_room_layout`
- `blender_list_assets`
- `blender_fit_object_to_bounds`
- `blender_inspect_scene`
- `blender_transform_object`
- `blender_duplicate_object`
- `blender_animate_object`
- `blender_set_render_preset`
- `blender_add_reference_image`
- `blender_apply_texture_material`
- `blender_apply_material_preset`
- `blender_setup_reference_camera`
- `blender_setup_compare_view`
- `blender_export_glb`
- `blender_export_obj`
- `blender_create_scene_from_reference`
- `blender_import_asset`
- `blender_render_scene`
- `blender_save_blend`
- `blender_inspect_rig`
- `blender_command`

The Blender add-on must still be enabled and the bridge must be running.

## Development Mode

Normal users only need `Start Bridge` and `Stop Bridge`.

For add-on development:

1. Enable `Developer Mode` in the add-on preferences or sidebar.
2. Set `Source File` to this repository's `blender_addon/codex_blender_addon.py`.
3. Click `Reload Bridge Code` after changing the add-on.

This avoids uninstalling and reinstalling the add-on during development.

## Troubleshooting

If the bridge is not reachable:

- Make sure Blender is open.
- Make sure `Codex Blender Bridge` is enabled.
- Click `Start Bridge` in the `Codex` sidebar tab.
- Check `http://127.0.0.1:8765/health`.

If an action says `Unsupported action`:

- Blender is running an older loaded copy of the add-on.
- In development mode, click `Reload Bridge Code`.
- For normal users, restart Blender or reinstall the updated add-on.

If a command returns `ObjectNotFound`, run `inspect_scene` and copy the exact object name from the response. If a command returns `PathNotFound`, check that the file exists and prefer project-relative paths such as `assets/models/sample_pyramid.obj`, `assets/textures/oak_wood_basecolor.png`, or `assets/references/modern_table_reference.png`.

If asset import fails:

- Put models under `assets/models/`.
- Use a supported file type: `.glb`, `.gltf`, `.fbx`, or `.obj`.
- Use a relative path like `assets/models/sample_pyramid.obj`, or an absolute path.

More detailed troubleshooting is in:

```text
docs/troubleshooting.md
```

## Textures

For quick blockouts, simple procedural colors are enough. For closer visual matches, put texture files under:

```text
assets/textures/
```

Recommended texture maps:

- `basecolor` or `albedo`: visible color.
- `roughness`: shine control.
- `normal`: fake surface detail such as wood grain or fabric weave.
- `metallic`: metal/non-metal control.
- `alpha`: transparency, useful for glass, decals, and cutouts.

Reference images should go under:

```text
assets/references/
```

`apply_texture_material` supports one base color image through `path` or `base_color_path`, plus optional `roughness_path`, `normal_path`, `metallic_path`, and `alpha_path`. Use it for user-supplied wood, fabric, stone, label, decal, or pattern images. Use `texture_scale`, `texture_offset`, `texture_rotation`, and `projection` to tune placement.

Built-in material presets are available through `apply_material_preset`:

- `wood_oak`
- `fabric_soft`
- `brushed_metal`
- `glass_clear`
- `matte_plastic`

If render or save output goes to the wrong place:

- Run the bridge command from the project folder.
- Use explicit output paths such as `renders/room.png` or `scenes/scene.blend`.
- On Windows, quote UNC paths and paths with spaces. See `docs/windows-paths.md`.

## Roadmap

- More reusable scene-building actions.
- Asset fitting and placement helpers.
- Material and texture helpers.
- Rigged model animation helpers.
- Packaging for easier local installation.
- A cleaner Codex plugin installation flow.
