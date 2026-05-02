# Codex Blender

Codex Blender is an open-source starter plugin for controlling Blender from Codex through local Python scripts and a localhost bridge.

The first version is intentionally simple:

- A Blender add-on starts a local HTTP server inside Blender.
- A bridge script sends JSON commands from the terminal or Codex workflow.
- Commands execute through Blender's Python API.
- Examples cover room creation and rig inspection.

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
  examples/inspect_rig.json
```

## Setup

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

## Send A Command

From this project folder:

```bash
python3 bridge/codex_blender_bridge.py examples/create_room.json
```

On Windows PowerShell:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
```

## Command Shape

```json
{
  "action": "create_room",
  "params": {
    "style": "modern_neon"
  }
}
```

Supported v0.1 actions:

- `ping`
- `create_room`
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

