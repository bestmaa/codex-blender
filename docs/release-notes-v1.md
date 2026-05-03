# Codex Blender v1.0.0 Release Notes

Codex Blender v1.0.0 is the first stable release of the local Blender bridge for creating, editing, inspecting, rendering, saving, importing, and exporting Blender scenes from Codex or a terminal command.

This is local automation. Blender must be installed, open, and running the `Codex Blender Bridge` add-on for live commands to work.

## Highlights

- Local HTTP bridge at `http://127.0.0.1:8765`.
- Blender add-on sidebar controls for `Start Bridge`, `Stop Bridge`, and development-only `Reload Bridge Code`.
- Starter room, outdoor road scene, furniture set, room layout presets, and reusable table, chair, sofa, plant, and lamp model actions.
- Scene inspection, object transform, duplication, fitting, and basic keyframe animation.
- Reference image planes, reference camera setup, and compare-view rendering workflows.
- Texture material support for user-provided images, multi-map materials, UV controls, and built-in material presets.
- Local model import for `.glb`, `.gltf`, `.fbx`, and `.obj`.
- Render presets, PNG rendering, `.blend` saving, `.glb` export, and `.obj` export.
- MCP tools and a Codex skill for stable workflows.
- Optional live bridge smoke test script.

## Installation

1. Download or build:

```text
dist/codex_blender_addon_v1.0.0.zip
```

2. In Blender, open:

```text
Edit > Preferences > Add-ons > Install
```

3. Select the ZIP, enable `Codex Blender Bridge`, open the 3D Viewport sidebar with `N`, then click `Start Bridge` in the `Codex` tab.

4. Check health:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
```

## Upgrade Notes

- Reinstall the latest add-on ZIP or source file when upgrading from older local builds.
- If using source development mode, set `Source File` to `blender_addon/codex_blender_addon.py` and use `Reload Bridge Code` after code changes.
- Restart Blender if an action returns `UnsupportedAction` after an update.
- Regenerate the ZIP with `python scripts\package_addon.py` after version changes.

## Known Limitations

- Procedural scene/model actions create useful blockouts and reusable primitives, not perfect production 3D models.
- A single image cannot reliably reconstruct a complete 3D scene. Use the reference image, model/import, texture, render, compare, and adjust workflow.
- Heavy renders depend on the local machine and may take time. Keep Blender and the computer awake during long renders.
- The bridge listens on localhost and is intended for trusted local workflows.
- `run_python` executes arbitrary Python inside Blender and should only be used with trusted local commands.

## Validation Before Release

Run:

```powershell
python scripts\validate_project.py
python scripts\smoke_test_bridge.py
python scripts\package_addon.py
```

The smoke test requires Blender to be open with the bridge running.
