# Codex Blender

Codex Blender is an open-source local bridge for controlling Blender from Codex or a terminal command. It runs a small HTTP server inside Blender, then accepts structured JSON commands for scene creation, asset import, rendering, saving, and inspection.

This is not a cloud connector. Blender runs locally on your machine.

## Features

- Start and stop a local Blender bridge at `http://127.0.0.1:8765`.
- Create a starter room scene.
- Create an outdoor road scene with trees and street lights.
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

Create a starter room:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
```

Create an outdoor road scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_outdoor_scene.json
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

Supported v0.7 actions:

- `ping`
- `create_room`
- `create_outdoor_scene`
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
