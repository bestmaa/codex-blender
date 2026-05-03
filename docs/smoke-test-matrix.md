# Final Smoke Test Matrix

Run this matrix before the v0.99 and v1.0 sequence.

## Required Commands

```powershell
python scripts\validate_project.py
python scripts\package_addon.py
python bridge\codex_blender_bridge.py examples\create_table_model.json
python bridge\codex_blender_bridge.py examples\apply_scaled_wood_texture.json
python bridge\codex_blender_bridge.py examples\add_reference_image.json
python bridge\codex_blender_bridge.py examples\render_scene.json
python bridge\codex_blender_bridge.py examples\save_blend.json
```

## Expected Outputs

```text
dist/codex_blender_addon_v0.98.5.zip
renders/room.png
scenes/scene.blend
```

## Pass Criteria

- Validation prints `All checks passed.`
- Package ZIP uses the current version.
- Blender bridge commands return `"ok": true`.
- Render and scene outputs are generated under ignored folders.
