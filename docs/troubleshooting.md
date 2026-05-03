# Troubleshooting

## Bridge Not Running

Symptom:

```text
Could not reach Blender bridge
```

Fix:

1. Open Blender.
2. Press `N` in the viewport.
3. Open the `Codex` tab.
4. Click `Start Bridge`.
5. Check health:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8765/health
```

## Unsupported Action After Code Update

Symptom:

```json
{
  "ok": false,
  "errorType": "UnsupportedAction"
}
```

Fix:

1. Enable Developer Mode in the Blender sidebar panel.
2. Click `Reload Bridge Code`.
3. Retry the command.

If reload is not available, reinstall the latest add-on ZIP or source file.

## Texture Or Asset Path Not Found

Symptom:

```text
Asset not found
```

Fix:

- Put models in `assets/models/`.
- Put textures in `assets/textures/`.
- Put reference images in `assets/references/`.
- Use project-relative paths such as `assets/textures/oak_wood_basecolor.png`.

## Object Name Not Found

Symptom:

```text
Object not found
```

Fix:

Inspect the scene before editing:

```powershell
python bridge\codex_blender_bridge.py examples\inspect_scene.json
```

Then use the exact object name returned by Blender.

## Render Timeout

Symptom:

```text
timed out
```

Fix:

Use a lower render preset before rendering:

```powershell
python bridge\codex_blender_bridge.py examples\set_render_preset.json
```

Or lower `samples` and `resolution` in the render command.
