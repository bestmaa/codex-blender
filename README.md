# Codex Blender

Codex Blender is an open-source starter plugin for controlling Blender from Codex through local Python scripts and a localhost bridge.

The first version is intentionally simple:

- A Blender add-on starts a local HTTP server inside Blender.
- A bridge script sends JSON commands from the terminal or Codex workflow.
- Commands execute through Blender's Python API.
- Examples cover room creation, outdoor scene creation, scene rendering, scene saving, and rig inspection.

## Project Status

This is an early scaffold. It is not a cloud connector yet. It is a local bridge that can become a proper Codex plugin workflow over time.

## Layout

```text
codex-blender/
  .codex-plugin/plugin.json
  skills/blender/SKILL.md
  blender_addon/codex_blender_addon.py
  bridge/codex_blender_bridge.py
  examples/create_room.json
  examples/create_outdoor_scene.json
  examples/render_scene.json
  examples/save_blend.json
  examples/inspect_rig.json
```

## Setup

### Blender

1. Open Blender.
2. Go to `Edit > Preferences > Add-ons > Install`.
3. Select `blender_addon/codex_blender_addon.py`.
4. Enable the add-on named `Codex Blender Bridge`.
5. In Blender, open the sidebar panel: `View3D > Sidebar > Codex`.
6. Click `Start Bridge`.

By default the bridge listens on:

```text
http://127.0.0.1:8765
```

During development, enable `Developer Mode`, set `Source File` in the Codex sidebar to this repository's `blender_addon/codex_blender_addon.py`, then click `Reload Bridge Code` after editing the add-on. This reloads the bridge without uninstalling and reinstalling the add-on. Developer controls are hidden by default for normal use.

### Codex

This repository includes a local MCP server in `.mcp.json`. When this plugin is enabled in Codex, it exposes tools for:

- `blender_health`
- `blender_create_room`
- `blender_create_outdoor_scene`
- `blender_render_scene`
- `blender_save_blend`
- `blender_inspect_rig`
- `blender_command`

The Blender add-on still needs to be running before those tools can control Blender.

## Send A Command

From this project folder:

```bash
python3 bridge/codex_blender_bridge.py examples/create_room.json
```

On Windows PowerShell:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
```

Create an outdoor road scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_outdoor_scene.json
```

Render the current Blender scene:

```powershell
python bridge\codex_blender_bridge.py examples\render_scene.json
```

Relative render outputs are resolved from the folder where the bridge command is run. From the project folder, `renders/room.png` writes to `codex-blender/renders/room.png`.

Save the current Blender scene:

```powershell
python bridge\codex_blender_bridge.py examples\save_blend.json
```

Relative `.blend` outputs are resolved from the folder where the bridge command is run. From the project folder, `scenes/scene.blend` writes to `codex-blender/scenes/scene.blend`.

## Command Shape

```json
{
  "action": "create_room",
  "params": {
    "style": "modern_neon"
  }
}
```

Supported v0.6 actions:

- `ping`
- `create_room`
- `create_outdoor_scene`
- `render_scene`
- `save_blend`
- `inspect_rig`
- `run_python`

`run_python` is powerful and unsafe. Use it only with trusted local commands.

## Roadmap

- Prompt-to-command templates for common Blender workflows.
- Asset import and scene fitting.
- Material and texture helpers.
- Rigged model animation helpers.
- Render automation.
- MCP server integration for richer Codex tool calls.
