# Known Limitations

Codex Blender is a local automation bridge for Blender. It is useful for repeatable commands, procedural blockouts, reference workflows, local asset handling, rendering, and exports. It is not a complete 3D reconstruction system.

## Image-To-3D Expectations

A single image cannot perfectly reconstruct a full 3D model or scene. One image hides the back, sides, depth, exact dimensions, material properties, and many lighting details.

The practical workflow is iterative:

1. Add the image as a reference with `add_reference_image`.
2. Create a procedural blockout or import a base model.
3. Apply textures or material presets.
4. Set up a matching camera with `setup_reference_camera` or `setup_compare_view`.
5. Render, compare, adjust, and repeat.

For closer matches, use real 3D assets, multiple reference views, measured dimensions, and user-provided textures.

## Local Blender Requirement

Blender must be open, the add-on must be enabled, and the bridge must be running for live commands to work.

The bridge health URL is:

```text
http://127.0.0.1:8765/health
```

If Blender is closed, asleep, or the bridge is stopped, Codex and terminal commands cannot edit the scene.

## Render And Long Task Limits

Rendering uses the local machine. Heavy scenes, high samples, high resolution, glass, shadows, and large assets can take time.

Keep the computer awake during long renders or smoke tests. Use `set_render_preset` with `draft` or `preview` before expensive iterations.

## Procedural Model Limits

Built-in model actions create reusable approximations:

- room and outdoor scenes
- table, chair, sofa, plant, and lamp models
- furniture layouts and reference-plan scenes

These are good starting points and test assets. They are not production-grade photoreal furniture, architecture, rigging, or CAD models.

## Trusted Local Automation

`run_python` can execute arbitrary Python inside Blender. Use it only for trusted local development and diagnostics. Prefer stable structured actions and MCP tools for normal workflows.
