# Render Comparison Loop

Reference matching should be treated as an iteration loop, not a single command. The goal is to make each render easier to compare against a target image and to keep the adjustment history organized.

## Workflow

1. Put the reference image under `assets/references/`.
2. Add it to Blender with `add_reference_image`.
3. Build or import the approximate model.
4. Use `setup_reference_camera` or `setup_compare_view`.
5. Render a preview with stable resolution and samples.
6. Compare reference and render.
7. Adjust geometry, scale, camera, lighting, material, texture placement, or color.
8. Render again with an incremented comparison name.

## Output Folders

Use generated comparison output folders:

```text
renders/compare/
renders/compare/reports/
```

These folders are generated output and should not be committed by default.

Recommended names:

```text
renders/compare/table_ref_v001.png
renders/compare/table_render_v001.png
renders/compare/table_side_by_side_v001.png
renders/compare/reports/table_v001.json
```

Increment the version when the model, material, camera, or lighting changes:

```text
v001
v002
v003
```

## What To Compare

Check the largest visual differences first:

- Camera angle and focal length.
- Object proportions and silhouette.
- Main material color and roughness.
- Texture scale, offset, and rotation.
- Light direction, shadow softness, and exposure.
- Missing details that affect the outline.

Do not tune tiny texture details while the model scale or camera is still wrong.

## Commands

Set camera:

```powershell
python bridge\codex_blender_bridge.py examples\setup_reference_camera.json
```

Render:

```powershell
python bridge\codex_blender_bridge.py examples\render_table_compare.json
```

For image-to-3D workflows, use the generated model import workflow first, then render comparisons from the imported object.

## Comparison Notes

Each iteration should record:

- Reference path.
- Render path.
- Camera settings.
- Object names adjusted.
- Material or texture changes.
- Human notes on what still differs.

Later tasks can automate side-by-side images and numeric metrics, but the folder and naming convention should stay stable.

## Contact Sheet

Create a side-by-side PNG from two existing PNG files:

```powershell
python scripts\create_contact_sheet.py assets\references\modern_table_reference.png renders\image_to_3d_mock_import.png renders\compare\table_side_by_side_v001.png --reference-label Reference --render-label Render --metadata-output renders\compare\reports\table_v001.json
```

The script writes the combined PNG plus optional JSON metadata containing source paths, labels, output size, and gap.
