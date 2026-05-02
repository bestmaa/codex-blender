# Codex Blender

Codex Blender is an open-source local bridge for controlling Blender from Codex or a terminal command. It runs a small HTTP server inside Blender, then accepts structured JSON commands for scene creation, asset import, rendering, saving, and inspection.

This is not a cloud connector. Blender runs locally on your machine.

## Features

- Start and stop a local Blender bridge at `http://127.0.0.1:8765`.
- Create a starter room scene.
- Create an outdoor road scene with trees and street lights.
- Create a reusable modern wooden table model.
- Add reference images as textured planes for side-by-side modeling.
- Apply user-provided image textures to Blender objects.
- Create approximate scenes from structured reference-image plans.
- Import local `.glb`, `.gltf`, `.fbx`, and `.obj` assets.
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
renders/        generated PNG renders
scenes/         generated .blend files
```

`renders/` and `scenes/` are ignored by Git.

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

For v0.7.0, download:

```text
codex_blender_addon_v0.7.0.zip
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

## Use From Terminal

Run commands from the project folder.

For a complete smoke test, see:

```text
docs/quickstart-demo.md
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

Supported v0.15 actions:

- `ping`
- `create_room`
- `create_outdoor_scene`
- `create_table_model`
- `add_reference_image`
- `apply_texture_material`
- `apply_material_preset`
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
- `blender_add_reference_image`
- `blender_apply_texture_material`
- `blender_apply_material_preset`
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

If asset import fails:

- Put models under `assets/models/`.
- Use a supported file type: `.glb`, `.gltf`, `.fbx`, or `.obj`.
- Use a relative path like `assets/models/car.glb`, or an absolute path.

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

## Roadmap

- More reusable scene-building actions.
- Asset fitting and placement helpers.
- Material and texture helpers.
- Rigged model animation helpers.
- Packaging for easier local installation.
- A cleaner Codex plugin installation flow.
