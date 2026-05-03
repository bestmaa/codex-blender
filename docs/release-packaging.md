# Release Packaging

Use this checklist before sharing a Blender add-on ZIP.

## 1. Validate The Project

```powershell
python scripts\validate_project.py
```

This checks Python syntax, JSON examples, version alignment, README paths, skill coverage, and package ZIP contents.

## 2. Build The Add-On ZIP

```powershell
python scripts\package_addon.py
```

The output path is:

```text
dist/codex_blender_addon_v<VERSION>.zip
```

The ZIP must contain only:

```text
codex_blender_addon.py
```

## 3. Install Test

In Blender:

```text
Edit > Preferences > Add-ons > Install
```

Select the ZIP from `dist/`, enable `Codex Blender Bridge`, then start the bridge from the `Codex` sidebar tab.

## 4. Smoke Test

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
python bridge\codex_blender_bridge.py examples\create_room.json
python bridge\codex_blender_bridge.py examples\render_scene.json
```
