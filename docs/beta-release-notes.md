# v0.97.0 Release Candidate Notes

Codex Blender v0.97.0 is the final packaging release candidate for the local Blender bridge before v1.0.

## Included Workflows

- Local Blender bridge health checks and JSON command execution.
- Starter room, outdoor road, reusable furniture models, furniture sets, and room layout presets.
- Reference image planes, reference camera setup, and side-by-side comparison rendering.
- Image texture materials, multi-map textures, and built-in material presets.
- Asset listing, import, fitting, object inspection, transforms, duplication, and basic keyframe animation.
- Render presets, PNG renders, `.blend` saves, `.glb` export, and `.obj` export.
- Codex skill instructions and MCP wrappers for stable actions.

## Install

Build or download:

```text
dist/codex_blender_addon_v0.97.0.zip
```

Install in Blender:

```text
Edit > Preferences > Add-ons > Install
```

Then enable `Codex Blender Bridge` and click `Start Bridge`.

## Known Limits

- Procedural model actions create useful blockouts, not production-grade photoreal models.
- Reference-image matching is iterative and depends on model primitives, textures, and camera setup.
- Blender must stay open with the bridge running for Codex/MCP commands to work.
- `run_python` is trusted local automation and should only be used with code generated in the current workflow.

## Validation

Before publishing a release candidate ZIP:

```powershell
python scripts\validate_project.py
python scripts\package_addon.py
```
