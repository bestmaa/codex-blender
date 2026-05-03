# Windows And WSL Paths

Use project-relative paths inside JSON commands whenever possible. They are shorter, portable between Windows and WSL, and are normalized by the bridge before the command is sent to Blender.

Good:

```json
{
  "action": "render_scene",
  "params": {
    "output": "renders/room.png"
  }
}
```

Good:

```json
{
  "action": "apply_texture_material",
  "params": {
    "object": "rounded rectangular tabletop",
    "base_color_path": "assets/textures/wood_basecolor.png",
    "roughness_path": "assets/textures/wood_roughness.png",
    "normal_path": "assets/textures/wood_normal.png"
  }
}
```

## PowerShell

Run commands from the project folder when you can:

```powershell
python bridge\codex_blender_bridge.py examples\create_room.json
python bridge\codex_blender_bridge.py examples\render_scene.json
```

Quote UNC paths, paths with spaces, and paths that contain many backslashes:

```powershell
python "\\wsl.localhost\Ubuntu\home\aditya\projects\codex-blender\bridge\codex_blender_bridge.py" "\\wsl.localhost\Ubuntu\home\aditya\projects\codex-blender\examples\create_room.json"
```

Prefer JSON files over inline JSON in PowerShell. If inline JSON is unavoidable, use a here-string or write the command to a file first so quotes do not need heavy escaping.

## Normalized Paths

The terminal bridge normalizes project-relative paths for:

- reference image paths used by `add_reference_image`
- texture paths used by `apply_texture_material`
- imported model paths used by `import_asset`
- render output paths used by `render_scene`
- saved scene output paths used by `save_blend`
- exported model output paths used by `export_glb` and `export_obj`

The MCP server applies the same normalization for its stable Blender tools and for matching generic `blender_command` actions.

## Folder Conventions

Use these project folders:

```text
assets/models/      input 3D models
assets/textures/    texture images
assets/references/  reference images
exports/            generated model exports
renders/            generated PNG renders
scenes/             generated .blend files
```

Avoid mixing unrelated path styles in one JSON command. For example, keep paths project-relative, or make every path absolute. Blender-native paths beginning with `//` are passed through unchanged.
