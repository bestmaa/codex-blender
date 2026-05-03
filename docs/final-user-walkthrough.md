# Final User Walkthrough

Use this before cutting v1 to check the project as a new local user would.

## 1. Install Or Reload The Add-On

Build the ZIP:

```powershell
python scripts\package_addon.py
```

Install in Blender:

```text
Edit > Preferences > Add-ons > Install
```

Select the generated ZIP from `dist/`, enable `Codex Blender Bridge`, then open the 3D Viewport sidebar with `N`.

For source development, enable Developer Mode, set `Source File` to `blender_addon/codex_blender_addon.py`, and click `Reload Bridge Code`.

## 2. Start And Check The Bridge

In Blender's `Codex` sidebar tab, click `Start Bridge`.

Check health:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
```

Expected:

```json
{
  "ok": true,
  "message": "Codex Blender Bridge is healthy."
}
```

## 3. Run Core Terminal Examples

From the project folder:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
python bridge\codex_blender_bridge.py examples\render_scene.json
python bridge\codex_blender_bridge.py examples\save_blend.json
```

Expected outputs:

```text
renders/room.png
scenes/scene.blend
```

## 4. Run The Optional Smoke Test

```powershell
python scripts\smoke_test_bridge.py
```

This checks health, creates a table, applies a texture, adds a reference image, renders, and saves a `.blend`.

## 5. Validate Before Release

```powershell
python scripts\validate_project.py
python scripts\package_addon.py
```

The package ZIP should match the current project version.
