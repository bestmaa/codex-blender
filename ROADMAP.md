# Codex Blender Roadmap

This roadmap keeps development focused on a practical v1.0 release.

## v1 Goal

Codex Blender v1.0 should let a user control Blender locally from Codex with reliable commands for:

- Creating reusable simple models.
- Adding reference images for visual matching.
- Applying image textures to objects.
- Importing local assets.
- Rendering and saving scenes.
- Exporting reusable models.
- Running a documented reference-to-scene workflow.

## Milestones

### Foundation

- Local Blender bridge.
- Codex skill.
- MCP server.
- Basic room/outdoor scenes.
- Render and save commands.
- Import local assets.

### Modeling

- Reusable table model.
- Reusable chair model.
- Furniture set scene.
- Stable object names for later material edits.

### Reference Workflow

- Add image as reference plane.
- Place camera for side-by-side comparison.
- Document repeatable image-to-scene workflow.

### Materials And Textures

- Apply user-provided image as texture.
- Add texture scale/offset/rotation controls.
- Add common material presets.
- Keep texture files under `assets/textures/`.

### Asset Workflow

- List local model/reference/texture assets.
- Import assets with transform controls.
- Export generated work as `.glb`.

### Release

- Validate project.
- Package add-on ZIP.
- Update docs.
- Tag and publish v1.0.0.

## Development Policy

- Use `TASKS.md` as the source of truth for task order.
- Do not batch unrelated roadmap items into one commit.
- Every user-facing action needs:
  - add-on support
  - bridge path handling when paths are involved
  - MCP tool support
  - example JSON
  - README update
  - skill update
  - validation coverage
  - live bridge test when possible

## Post-v1 Ideas

- Hunyuan3D or Stable Fast 3D adapter.
- Poly Haven/HDRI helpers.
- Material node graphs with normal/roughness maps.
- Rig animation presets.
- Scene diff/compare automation.
- Better Codex plugin installation flow.
