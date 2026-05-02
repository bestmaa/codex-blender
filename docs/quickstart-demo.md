# Quickstart Demo

This demo verifies the full local workflow:

```text
Start Bridge -> Create Scene -> Import Asset -> Render PNG -> Save .blend
```

## 1. Install And Start The Bridge

Install the add-on in Blender from the release ZIP or source file:

```text
Edit > Preferences > Add-ons > Install
```

Enable `Codex Blender Bridge`, then open the Blender viewport sidebar:

```text
N key > Codex tab > Start Bridge
```

Confirm the bridge is healthy:

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

## 2. Run The Demo Commands

Run these commands from the project folder.

Create an outdoor scene:

```powershell
python bridge\codex_blender_bridge.py examples\create_outdoor_scene.json
```

Import the sample OBJ asset:

```powershell
python bridge\codex_blender_bridge.py examples\import_asset.json
```

Render the scene:

```powershell
python bridge\codex_blender_bridge.py examples\render_scene.json
```

Save the scene:

```powershell
python bridge\codex_blender_bridge.py examples\save_blend.json
```

## 3. Expected Outputs

Render output:

```text
renders/room.png
```

Saved Blender scene:

```text
scenes/scene.blend
```

Both output folders are ignored by Git.

## 4. Useful Variations

Change road size and object counts in:

```text
examples/create_outdoor_scene.json
```

Change the imported model path in:

```text
examples/import_asset.json
```

Models should normally live in:

```text
assets/models/
```

Supported import formats:

```text
.glb
.gltf
.fbx
.obj
```

## 5. Troubleshooting

If a command cannot reach Blender:

```text
Click Start Bridge in Blender's Codex sidebar tab.
```

If a command returns `Unsupported action`:

```text
Reload the add-on code in Developer Mode, or reinstall the latest add-on ZIP.
```

If asset import fails:

```text
Check that the model file exists and uses a supported extension.
```
