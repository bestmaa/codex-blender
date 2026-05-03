# Reference Comparison Workflow

Use this workflow when matching a generated or user-provided image with a Blender model.

## 1. Save The Reference Image

Put stable reference images in:

```text
assets/references/
```

Use descriptive names such as:

```text
assets/references/modern_table_reference.png
```

One-off experiments can stay local, but stable examples should reference files that are kept in the repository.

## 2. Create The Base Model

Start with the closest supported model action.

```powershell
python bridge\codex_blender_bridge.py examples\create_table_model.json
```

For furniture scenes, use:

```powershell
python bridge\codex_blender_bridge.py examples\create_furniture_set.json
```

## 3. Add The Reference Plane

Add the image as a visible plane in the Blender scene.

```powershell
python bridge\codex_blender_bridge.py examples\add_reference_image.json
```

The reference plane should be named clearly, for example:

```text
table reference image
```

## 4. Apply Materials Or Textures

Use material presets for fast iteration:

```powershell
python bridge\codex_blender_bridge.py examples\apply_material_preset.json
```

Use image textures when a generated or user-provided texture should drive the surface:

```powershell
python bridge\codex_blender_bridge.py examples\apply_table_texture.json
```

For physically richer assets, use multi-map texture inputs:

```powershell
python bridge\codex_blender_bridge.py examples\apply_multimap_wood_texture.json
```

## 5. Set Up The Compare View

Use side-by-side comparison when matching shape, proportion, and camera angle:

```powershell
python bridge\codex_blender_bridge.py examples\setup_compare_view.json
```

Use the reference camera when matching the render framing:

```powershell
python bridge\codex_blender_bridge.py examples\setup_reference_camera.json
```

## 6. Render And Compare

Render the comparison output:

```powershell
python bridge\codex_blender_bridge.py examples\render_table_compare.json
```

Expected output:

```text
renders/table_compare.png
```

## 7. Iterate Safely

Before changing geometry, inspect the scene:

```powershell
python bridge\codex_blender_bridge.py examples\inspect_scene.json
```

Use narrow edits for object placement:

```powershell
python bridge\codex_blender_bridge.py examples\transform_tabletop.json
```

Then render again and compare. Keep experimental commands in:

```text
examples/dev/
```

Move only stable, reusable command files back into `examples/` and add them to validation.
