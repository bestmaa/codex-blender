# Codex Blender Task Queue

This queue is the working contract for taking Codex Blender to v1.0 in small verified steps.

## Operating Rules

- Work on exactly one task at a time.
- Pick the first task with `Status: pending`.
- Change its status to `in_progress` before editing code.
- Auto mode is enabled by default: after a task is implemented, verified, and committed, start the next pending task automatically.
- Do not start the next task until the current task is implemented, verified, and committed.
- If verification fails, keep the same task `in_progress` and fix it before moving on.
- Stop auto mode only when verification fails, a blocker appears, Blender/bridge is unavailable, Git fails, or the user says stop/pause/review.
- Keep changes scoped to the current task.
- Preserve user changes and unrelated worktree changes.
- Prefer structured bridge actions over trusted `run_python` scripts when adding reusable features.
- Update docs, examples, skill instructions, MCP tools, validation, and package version when a user-facing action changes.
- After every completed task, commit with the listed commit message.

## Standard Verification

Run these checks for every code task unless the task explicitly says otherwise:

```powershell
python -m py_compile blender_addon\codex_blender_addon.py bridge\codex_blender_bridge.py scripts\codex_blender_mcp.py scripts\validate_project.py
python scripts\validate_project.py
```

For Blender behavior tasks, also verify with the live bridge:

```powershell
python bridge\codex_blender_bridge.py examples\<task-example>.json
python bridge\codex_blender_bridge.py examples\render_<task>.json
```

If the add-on code changed while Blender is already running, reload first:

```json
{
  "action": "run_python",
  "params": {
    "code": "import bpy\nbpy.ops.codex_blender.reload_bridge_code()\n"
  }
}
```

## Queue

### 1. v0.12 Commit Current Table, Reference, And Texture Workflow

Status: completed

Goal:
Capture the current working state that added table modeling, reference image planes, and single-image texture application.

Scope:
- Review uncommitted files.
- Keep source, docs, examples, reference assets, and texture assets that are useful for demos.
- Avoid committing generated `renders/`, `scenes/`, and `dist/`.
- Run project validation.
- Commit the stable plugin/source/docs/example changes.

Verify:
- `python scripts\validate_project.py` passes.
- `create_table_model`, `add_reference_image`, and `apply_texture_material` examples work against the live bridge.

Commit:
`Add table reference and texture workflows`

### 2. v0.13 UV Texture Controls

Status: completed

Goal:
Improve texture application so user-provided images can be scaled, rotated, and positioned on a mesh surface.

Scope:
- Extend `apply_texture_material` params:
  - `texture_scale`: `[x, y]`, default `[1, 1]`
  - `texture_offset`: `[x, y]`, default `[0, 0]`
  - `texture_rotation`: number in radians, default `0`
  - `projection`: default `uv`
- Add Blender shader nodes for texture coordinate/mapping when possible.
- Keep backward compatibility with existing `apply_texture_material` JSON.
- Add `examples/apply_scaled_wood_texture.json`.
- Update MCP tool schema, README, skill, and validation.

Verify:
- Apply generated wood texture with scale controls.
- Render `renders/scaled_wood_table.png`.
- Validation passes.

Commit:
`Add UV texture controls`

### 3. v0.14 Texture Folder And Material Presets

Status: completed

Goal:
Make texture usage easier by documenting folders and adding preset materials for common surfaces.

Scope:
- Add `assets/textures/.gitkeep` if needed.
- Add `apply_material_preset`.
- Presets:
  - `wood_oak`
  - `fabric_soft`
  - `brushed_metal`
  - `glass_clear`
  - `matte_plastic`
- Apply presets by object name.
- Update MCP, examples, README, skill, validation.

Verify:
- Preset examples apply to table objects.
- Render one preset demo.
- Validation passes.

Commit:
`Add material presets`

### 4. v0.15 Multi-Map Texture Materials

Status: completed

Goal:
Support real PBR-style texture sets, not only one base color image.

Scope:
- Extend material texture action to accept:
  - `base_color_path`
  - `roughness_path`
  - `normal_path`
  - `metallic_path`
  - `alpha_path`
- Keep existing `path` alias for base color.
- Add normal map node wiring.
- Update bridge/MCP/docs/examples/validation.

Verify:
- Base color only still works.
- Base color + normal example works if a sample normal image exists.
- Validation passes.

Commit:
`Add multi-map texture materials`

### 5. v0.16 Reference Image Camera Helper

Status: completed

Goal:
Make image matching easier by adding a helper to place camera and reference plane together.

Scope:
- Add action `setup_reference_camera`.
- Params:
  - `reference_object`
  - `camera_location`
  - `target`
  - `lens`
  - `resolution`
- Optional: add a camera target empty.
- Update MCP, examples, README, skill, validation.

Verify:
- Add reference image, create table, setup camera, render.
- Reference/model comparison is visible.
- Validation passes.

Commit:
`Add reference camera setup`

### 6. v0.17 Reference Overlay Compare Render

Status: completed

Goal:
Create a practical compare render that shows reference and 3D model together.

Scope:
- Add action `setup_compare_view`.
- Support side-by-side placement or background reference placement.
- Add example for table comparison.
- Update docs and skill.

Verify:
- Render `renders/table_compare.png`.
- Model and reference are both visible.
- Validation passes.

Commit:
`Add reference compare view`

### 7. v0.18 Export GLB

Status: completed

Goal:
Allow generated scenes/models to be exported for use outside Blender.

Scope:
- Add action `export_glb`.
- Params:
  - `output`
  - `selected_only`
  - `include_materials`
- Normalize output paths in bridge and MCP.
- Add example `examples/export_table_glb.json`.
- Update docs and validation.

Verify:
- Create table.
- Export `exports/modern_table.glb`.
- Confirm output file exists and is non-empty.
- Validation passes.

Commit:
`Add GLB export action`

### 8. v0.19 Export OBJ

Status: completed

Goal:
Add a simple OBJ export path for compatibility.

Scope:
- Add action `export_obj`.
- Params:
  - `output`
  - `selected_only`
- Normalize output paths in bridge and MCP.
- Add example `examples/export_table_obj.json`.
- Update docs and validation.

Verify:
- Create table.
- Export `exports/modern_table.obj`.
- Confirm output file exists and is non-empty.
- Validation passes.

Commit:
`Add OBJ export action`

### 9. v0.20 Chair Model Action

Status: completed

Goal:
Add a reusable chair model action to pair with the table.

Scope:
- Add `create_chair_model`.
- Include seat, back, legs, bevels, material options, camera/light defaults.
- Add example JSON and render example.
- Add MCP, docs, skill, validation.

Verify:
- Create chair model.
- Render `renders/modern_chair.png`.
- Save `.blend`.
- Validation passes.

Commit:
`Add reusable chair model action`

### 10. v0.21 Sofa Model Action

Status: completed

Goal:
Add a reusable sofa/couch model for room scenes.

Scope:
- Add `create_sofa_model`.
- Params for size, cushions, color/material preset.
- Add stable object names for cushions, arms, legs.
- Add MCP, examples, docs, validation.

Verify:
- Create sofa.
- Render `renders/modern_sofa.png`.
- Validation passes.

Commit:
`Add reusable sofa model action`

### 11. v0.22 Plant Model Action

Status: completed

Goal:
Add a reusable indoor plant model.

Scope:
- Add `create_plant_model`.
- Include pot, trunk/stem, leaf clusters.
- Params for height, leaf color, pot style.
- Add examples/docs/MCP/validation.

Verify:
- Create plant.
- Render `renders/indoor_plant.png`.
- Validation passes.

Commit:
`Add reusable plant model action`

### 12. v0.23 Lamp And Light Fixture Action

Status: completed

Goal:
Add reusable lamps/light fixtures for scenes.

Scope:
- Add `create_lamp_model`.
- Support floor lamp, table lamp, ceiling panel.
- Include real Blender light objects where useful.
- Add examples/docs/MCP/validation.

Verify:
- Create lamp.
- Render shows visible lighting.
- Validation passes.

Commit:
`Add reusable lamp model action`

### 13. v0.24 Furniture Set Action

Status: completed

Goal:
Create a basic furniture scene from reusable primitives.

Scope:
- Add `create_furniture_set`.
- Compose table, chairs, plant, rug/floor, lights, camera.
- Keep object names stable for later texture application.
- Add examples and docs.

Verify:
- Create set with table and four chairs.
- Render `renders/furniture_set.png`.
- Validation passes.

Commit:
`Add furniture set scene action`

### 14. v0.25 Room Layout Presets

Status: completed

Goal:
Create reusable room layout presets.

Scope:
- Add action `create_room_layout`.
- Presets:
  - `studio`
  - `living_room`
  - `office`
  - `gallery`
- Include floor/walls/camera/lighting.
- Add examples/docs/MCP/validation.

Verify:
- Each preset creates a scene.
- One preset render exists.
- Validation passes.

Commit:
`Add room layout presets`

### 15. v0.26 Asset Library Helpers

Status: completed

Goal:
Make local assets easier to discover and import.

Scope:
- Add action `list_assets`.
- Support folders:
  - `assets/models/`
  - `assets/textures/`
  - `assets/references/`
- Return filename, type, size, and relative path.
- Add optional filters by extension/type.
- Add MCP tool and docs.

Verify:
- List existing sample model, reference images, and generated texture.
- Validation passes.

Commit:
`Add asset library helpers`

### 16. v0.27 Asset Placement Helpers

Status: completed

Goal:
Make imported assets easier to place and scale.

Scope:
- Add action `fit_object_to_bounds`.
- Params:
  - `object`
  - `target_size`
  - `target_location`
  - `align_to_floor`
- Add example using sample asset.
- Update MCP/docs/validation.

Verify:
- Import sample asset.
- Fit and align it to floor.
- Validation passes.

Commit:
`Add asset placement helpers`

### 17. v0.28 Scene Object Inspection

Status: completed

Goal:
Let Codex inspect current scene objects before editing.

Scope:
- Add action `inspect_scene`.
- Return objects with name, type, location, dimensions, material names.
- Add MCP/docs/examples/validation.

Verify:
- Create table.
- Inspect scene returns table objects.
- Validation passes.

Commit:
`Add scene inspection action`

### 18. v0.29 Object Transform Action

Status: completed

Goal:
Allow precise movement/rotation/scaling of existing objects.

Scope:
- Add action `transform_object`.
- Params:
  - `object`
  - `location`
  - `rotation`
  - `scale`
  - `dimensions`
- Preserve unspecified transforms.
- Add MCP/docs/examples/validation.

Verify:
- Create table.
- Move/scale one named object.
- Render confirms change.
- Validation passes.

Commit:
`Add object transform action`

### 19. v0.30 Object Duplication And Arrangement

Status: completed

Goal:
Support repeated objects such as chair sets.

Scope:
- Add action `duplicate_object`.
- Params:
  - `object`
  - `count`
  - `offset`
  - `name_prefix`
- Add docs/examples/MCP/validation.

Verify:
- Duplicate a chair/table leg/sample object.
- Inspect scene confirms new objects.
- Validation passes.

Commit:
`Add object duplication action`

### 20. v0.31 Animation Basics

Status: completed

Goal:
Add simple object animation support.

Scope:
- Add action `animate_object`.
- Support location/rotation/scale keyframes.
- Add frame range params.
- Add example that animates a door/table object.
- Update MCP/docs/validation.

Verify:
- Animation keyframes are created.
- Save `.blend`.
- Validation passes.

Commit:
`Add basic object animation`

### 21. v0.32 Render Presets

Status: completed

Goal:
Make render quality easier to control.

Scope:
- Add action `set_render_preset`.
- Presets:
  - `draft`
  - `preview`
  - `final`
- Configure samples, resolution, engine, view transform.
- Update docs/examples/MCP/validation.

Verify:
- Apply preset and render.
- Validation passes.

Commit:
`Add render presets`

### 22. v0.33 Project Examples Cleanup

Status: completed

Goal:
Make examples consistent and useful.

Scope:
- Review all `examples/*.json`.
- Remove one-off experimental examples or move them to `examples/dev/`.
- Keep stable examples named clearly.
- Ensure validation covers stable examples only.
- Update README example list.

Verify:
- `python scripts\validate_project.py` passes.
- Stable examples all load as JSON.

Commit:
`Clean up command examples`

### 23. v0.34 Reference Workflow Documentation

Status: completed

Goal:
Document a repeatable workflow for image-to-model work.

Scope:
- Add `docs/reference-workflow.md`.
- Cover:
  - creating/saving reference images
  - adding reference plane
  - creating model
  - applying texture
  - rendering comparison
  - iterating safely
- Link from README.

Verify:
- Follow docs from a clean table scene.
- Render comparison output exists.
- Validation passes.

Commit:
`Document reference comparison workflow`

### 24. v0.35 Troubleshooting And UX Polish

Status: completed

Goal:
Improve user-facing troubleshooting for common local Blender issues.

Scope:
- Expand README troubleshooting.
- Add docs for:
  - bridge not running
  - unsupported action after code update
  - texture path not found
  - object name not found
  - render timeout
- Improve error messages where needed.

Verify:
- Validation passes.
- Error messages remain JSON responses from bridge.

Commit:
`Polish troubleshooting guidance`

### 25. v0.36 Validation Expansion

Status: completed

Goal:
Make validation catch more project drift before release.

Scope:
- Validate all stable example actions are supported.
- Validate README referenced files.
- Validate MCP version matches plugin version.
- Validate skill includes supported actions.
- Keep validation independent of launching Blender.

Verify:
- Intentionally inspect validation output.
- Validation passes.

Commit:
`Expand project validation`

### 26. v0.37 Packaging Polish

Status: completed

Goal:
Ensure add-on packaging is reliable for users.

Scope:
- Confirm package ZIP contains only required add-on file.
- Add package checks for versioned filename.
- Update install instructions if needed.
- Add release packaging notes.

Verify:
- `python scripts\package_addon.py` creates ZIP.
- `python scripts\validate_project.py` passes.

Commit:
`Polish add-on packaging`

### 27. v0.38 Skill And MCP Polish

Status: completed

Goal:
Make the Codex skill and MCP tool list clear and complete.

Scope:
- Review `skills/blender/SKILL.md`.
- Ensure each supported action has a concise JSON example.
- Review MCP tool descriptions and schemas.
- Update installed local skill copy.

Verify:
- MCP initializes.
- Tools list includes all stable actions.
- Validation passes.

Commit:
`Polish skill and MCP docs`

### 28. v0.39 Pre-Beta Cleanup

Status: completed

Goal:
Prepare for beta stabilization.

Scope:
- Remove stale experimental files from stable docs/validation.
- Ensure generated outputs are ignored.
- Ensure examples are minimal and useful.
- Review README top to bottom.

Verify:
- `git status` contains only intended changes before commit.
- Validation passes.

Commit:
`Prepare project for beta`

### 29. v0.90 Beta Release

Status: completed

Goal:
Mark the project as beta after core workflows are stable.

Scope:
- Set version to `0.90.0`.
- Update README supported actions.
- Build package ZIP.
- Add beta release notes.
- Do not tag unless requested.

Verify:
- Package ZIP exists.
- Validation passes.

Commit:
`Prepare v0.90.0 beta`

### 30. v0.91 Beta Bugfix Pass

Status: completed

Goal:
Fix issues discovered while using the beta features.

Scope:
- Run core workflows:
  - create table
  - apply texture
  - add reference image
  - export GLB
  - create furniture set
- Fix bugs only, no new feature scope.

Verify:
- Core workflows pass.
- Validation passes.

Commit:
`Fix beta workflow issues`

### 31. v0.92 Documentation Pass

Status: completed

Goal:
Make docs easy for a new user.

Scope:
- Rewrite quickstart if needed.
- Add clear first-run steps.
- Add common commands section.
- Add "what this plugin can/cannot do" section.

Verify:
- README links resolve.
- Validation passes.

Commit:
`Improve user documentation`

### 32. v0.93 Release Demo Assets

Status: completed

Goal:
Keep a small set of demo assets for release testing.

Scope:
- Keep one model asset, one reference image, one texture image.
- Avoid large binary files when possible.
- Document demo asset purpose.

Verify:
- Demo workflows can use included assets.
- Validation passes.

Commit:
`Add release demo assets`

### 33. v0.94 Release Candidate Checks

Status: completed

Goal:
Run final checks before release candidate.

Scope:
- Run validation.
- Build package.
- Smoke-test bridge actions.
- Check docs and examples.

Verify:
- Validation passes.
- Package ZIP exists.
- Smoke test outputs are generated locally.

Commit:
`Run release candidate checks`

### 34. v0.95 Release Candidate

Status: completed

Goal:
Prepare v1 release candidate.

Scope:
- Set version to `0.95.0`.
- Update release notes.
- Build package ZIP.
- Push branch if requested.

Verify:
- Validation passes.
- Package ZIP exists.

Commit:
`Prepare v0.95.0 release candidate`

### 35. v0.96 RC Bugfix Pass

Status: completed

Goal:
Fix release candidate bugs only.

Scope:
- No new features.
- Fix docs, examples, validation, or bridge bugs found in RC testing.

Verify:
- Validation passes.
- Any fixed workflow is re-tested.

Commit:
`Fix release candidate issues`

### 36. v0.97 Final Packaging Pass

Status: completed

Goal:
Make final package and release files clean.

Scope:
- Rebuild package.
- Confirm package file naming.
- Confirm README release download instructions.
- Confirm `.gitignore`.

Verify:
- Package ZIP exists.
- Validation passes.

Commit:
`Finalize package assets`

### 37. v0.98 Final Documentation Pass

Status: completed

Goal:
Make v1 docs ready.

Scope:
- Final README pass.
- Final quickstart pass.
- Final reference workflow pass.
- Final troubleshooting pass.

Verify:
- README paths pass validation.
- Validation passes.

Commit:
`Finalize v1 documentation`

### 38. v0.98.5 Final Smoke Test Matrix

Status: completed

Goal:
Define and run the final smoke test matrix before the v0.99 sequence.

Scope:
- List the exact workflows that must pass before v1.
- Run representative workflows:
  - table creation
  - texture apply
  - reference image add
  - render
  - save
  - package
- Update docs if the workflow names are confusing.

Verify:
- Validation passes.
- Package ZIP exists.
- Smoke test matrix is documented or listed in release notes draft.

Commit:
`Define final smoke test matrix`

### 39. v0.99 Final Pre-Release Check

Status: completed

Goal:
Ensure the repository is ready to enter the final v1 preparation sequence.

Scope:
- Run all local checks.
- Build package.
- Run core smoke tests.
- Confirm git status before release prep.

Verify:
- Validation passes.
- Package ZIP exists.
- Smoke test workflows pass.

Commit:
`Prepare final v1 release checks`

### 40. v0.99.1 Windows Path Polish

Status: completed

Goal:
Make Windows and WSL path handling clearer and more reliable.

Scope:
- Review UNC path examples.
- Ensure bridge path normalization covers references, textures, exports, renders, and scenes.
- Update troubleshooting for Windows PowerShell quoting.
- Add one path normalization test/example where practical.

Verify:
- Existing examples still work from PowerShell.
- Validation passes.

Commit:
`Polish Windows path handling`

### 41. v0.99.2 Error Response Polish

Status: completed

Goal:
Make bridge errors easier for users to understand.

Scope:
- Review common errors:
  - object not found
  - path not found
  - unsupported action
  - unsupported asset type
  - bad vector params
- Ensure errors return actionable messages.
- Update README troubleshooting if needed.

Verify:
- Trigger one safe error manually and confirm JSON message is clear.
- Validation passes.

Commit:
`Polish bridge error messages`

### 42. v0.99.3 Command Schema Documentation

Status: completed

Goal:
Document the stable bridge command schema before v1.

Scope:
- Add `docs/commands.md`.
- List every stable action, params, defaults, and output shape.
- Link from README.
- Keep examples concise.

Verify:
- README links resolve.
- Validation passes.

Commit:
`Document command schema`

### 43. v0.99.4 MCP Tool Audit

Status: completed

Goal:
Ensure MCP tools match stable bridge actions.

Scope:
- Compare `execute_command` actions against MCP tools.
- Add missing tools or document intentionally raw-only actions.
- Check tool descriptions and defaults.

Verify:
- MCP initializes.
- Tool list is complete.
- Validation passes.

Commit:
`Audit MCP tool coverage`

### 44. v0.99.5 Skill Workflow Audit

Status: completed

Goal:
Ensure the installed Blender skill tells Codex how to use all stable workflows.

Scope:
- Review `skills/blender/SKILL.md`.
- Add missing action examples.
- Add guidance for reference image, texture, export, and inspect workflows.
- Sync local installed skill.

Verify:
- Skill file includes stable actions.
- Validation passes.

Commit:
`Audit Blender skill workflow`

### 45. v0.99.6 Example Smoke Test Script

Status: completed

Goal:
Add one script to run stable examples in a predictable order when Blender is running.

Scope:
- Add `scripts/smoke_test_bridge.py`.
- Run health check.
- Run selected examples:
  - create table
  - apply texture
  - add reference
  - render
  - save
- Keep script optional and clearly documented.

Verify:
- Script runs against live bridge.
- Validation passes.

Commit:
`Add bridge smoke test script`

### 46. v0.99.7 Release Notes Draft

Status: completed

Goal:
Prepare release notes before v1.

Scope:
- Add `RELEASE_NOTES.md` or `docs/release-notes-v1.md`.
- Include features, installation, known limitations, and upgrade notes.
- Mention that Blender must be running locally.

Verify:
- README links resolve if linked.
- Validation passes.

Commit:
`Draft v1 release notes`

### 47. v0.99.8 Known Limitations Document

Status: completed

Goal:
Set correct expectations for AI image-to-3D and Blender automation.

Scope:
- Add docs section explaining:
  - single image cannot perfectly reconstruct full 3D scenes
  - reference/asset/texture workflow is the practical route
  - local Blender must remain open for live commands
  - heavy renders need machine awake
- Link from README.

Verify:
- Docs are linked.
- Validation passes.

Commit:
`Document known limitations`

### 48. v0.99.9 Repository Hygiene Pass

Status: completed

Goal:
Clean up repository state before v1.

Scope:
- Confirm `.gitignore` excludes generated renders/scenes/dist/exports.
- Confirm no accidental large generated files are tracked.
- Keep only intentional demo assets.
- Review `git status`.

Verify:
- Validation passes.
- `git status` only shows intended release changes before commit.

Commit:
`Clean repository before v1`

### 49. v0.99.10 Final Version Alignment

Status: completed

Goal:
Make version handling ready for the final v1 bump.

Scope:
- Check plugin manifest version.
- Check add-on `bl_info` version.
- Check MCP server version.
- Check package filename behavior.
- Add validation coverage if missing.

Verify:
- Validation catches version mismatch.
- Validation passes.

Commit:
`Finalize version alignment checks`

### 50. v0.99.11 Final User Walkthrough

Status: completed

Goal:
Run the project exactly like a new user would before v1.

Scope:
- Follow README install/use flow.
- Start bridge.
- Run core terminal examples.
- Render one image.
- Save one `.blend`.
- Package add-on.
- Note and fix any confusing docs.

Verify:
- New-user walkthrough succeeds.
- Validation passes.
- Package ZIP exists.

Commit:
`Complete final user walkthrough`

### 51. v1.0 Stable Release

Status: completed

Goal:
Cut the first stable release.

Scope:
- Set version to `1.0.0`.
- Update README supported actions and release notes.
- Build package ZIP.
- Commit release changes.
- Tag `v1.0.0`.
- Push branch and tag if requested.
- Create GitHub release with ZIP asset if requested.

Verify:
- Package ZIP exists.
- Validation passes.
- Git status is clean after commit/tag.

Commit:
`Release v1.0.0`

### 52. v1.1.0 BlenderMCP Compatibility Research

Status: completed

Goal:
Define what "BlenderMCP-compatible" means for this project before writing adapters.

Scope:
- Review common BlenderMCP-style command/tool names.
- Map likely commands to existing bridge actions.
- Identify commands that require new generic object/material/light helpers.
- Add `docs/blendermcp-compatibility.md`.

Verify:
- Compatibility doc lists supported, mapped, and unsupported command families.
- Validation passes.

Commit:
`Document BlenderMCP compatibility plan`

### 53. v1.1.1 BlenderMCP Payload Adapter

Status: completed

Goal:
Accept BlenderMCP-style payloads and translate safe ones into bridge actions.

Scope:
- Add adapter module/function for payload translation.
- Support health/ping, scene inspect, primitive create, render, save where practical.
- Return clear errors for unsupported payloads.
- Add examples under `examples/blendermcp/`.

Verify:
- Adapter unit/example checks pass.
- Validation passes.

Commit:
`Add BlenderMCP payload adapter`

### 54. v1.1.2 BlenderMCP Raw Tool Bridge

Status: completed

Goal:
Expose compatibility through MCP and terminal workflows.

Scope:
- Add MCP tool for compatible raw BlenderMCP payloads.
- Add terminal example for translated payload.
- Document when to use compatibility vs native actions.

Verify:
- MCP initializes.
- Tool list includes compatibility tool.
- Validation passes.

Commit:
`Expose BlenderMCP compatibility tool`

### 55. v1.1.3 BlenderMCP Compatibility Smoke Test

Status: completed

Goal:
Prove compatibility layer works against a running Blender bridge.

Scope:
- Add optional smoke test for compatibility payloads.
- Include inspect, create simple primitive, render, and save.
- Keep test optional and documented.

Verify:
- Smoke test succeeds against live bridge.
- Validation passes.

Commit:
`Add BlenderMCP compatibility smoke test`

### 56. v1.2.0 Procedural Primitive Library

Status: completed

Goal:
Add better reusable procedural primitive helpers for future models.

Scope:
- Add actions/helpers for bevelled boxes, cylinders, cones, planes, labels, panels, and simple glass.
- Standardize naming, materials, transforms, and dimensions.
- Add examples.

Verify:
- Examples create expected objects.
- Validation passes.

Commit:
`Add procedural primitive library`

### 57. v1.2.1 Procedural Furniture Expansion

Status: completed

Goal:
Expand built-in furniture generation beyond the initial v1 set.

Scope:
- Add reusable shelf, cabinet, desk, bed, door, window, and wall art actions or presets.
- Include basic material and size params.
- Add examples and README entries.

Verify:
- New examples run against live bridge.
- Validation passes.

Commit:
`Expand procedural furniture library`

### 58. v1.2.2 Procedural Architecture Expansion

Status: completed

Goal:
Add room and building-detail primitives for richer scenes.

Scope:
- Add walls with openings, floor tiles, ceiling panels, stairs, railings, and simple facade elements.
- Keep geometry procedural and lightweight.
- Add examples.

Verify:
- Architecture examples run.
- Validation passes.

Commit:
`Expand procedural architecture library`

### 59. v1.2.3 Procedural Outdoor Expansion

Status: completed

Goal:
Improve outdoor scene generation.

Scope:
- Add sidewalk, curb, road markings, benches, signs, bushes, rocks, and varied trees.
- Add params for density and style.
- Add render example.

Verify:
- Outdoor example runs and renders.
- Validation passes.

Commit:
`Expand procedural outdoor library`

### 60. v1.2.4 Procedural Library Catalog

Status: completed

Goal:
Make procedural assets discoverable from Codex and terminal.

Scope:
- Add action to list procedural presets/assets.
- Document categories and params.
- Add MCP wrapper if useful.

Verify:
- Catalog command returns expected categories.
- Validation passes.

Commit:
`Add procedural asset catalog`

### 61. v1.3.0 Asset Library Manifest

Status: completed

Goal:
Create a searchable local asset library format.

Scope:
- Add `assets/library.json` schema or index.
- Include name, type, tags, path, scale hints, license/source, preview path.
- Add validation for manifest paths.

Verify:
- Manifest validation passes.
- Validation passes.

Commit:
`Add asset library manifest`

### 62. v1.3.1 Asset Search Action

Status: completed

Goal:
Search local assets by name, tag, type, and extension.

Scope:
- Add bridge action for asset search.
- Add MCP wrapper.
- Add examples.

Verify:
- Search returns known sample assets.
- Validation passes.

Commit:
`Add asset search action`

### 63. v1.3.2 Asset Import From Search

Status: completed

Goal:
Make search-to-import workflow easy.

Scope:
- Add action to import by asset library id/name.
- Apply scale/location hints.
- Fit to bounds when requested.

Verify:
- Import-by-id example runs.
- Validation passes.

Commit:
`Add asset library import workflow`

### 64. v1.3.3 Asset Preview And Metadata Docs

Status: completed

Goal:
Document how users should add their own models, textures, and previews.

Scope:
- Add docs for asset folders, manifest entries, previews, tags, and licenses.
- Link from README.

Verify:
- README links resolve.
- Validation passes.

Commit:
`Document asset library workflow`

### 65. v1.4.0 Image-To-3D Integration Plan

Status: completed

Goal:
Design a provider-neutral image-to-3D integration before adding any vendor-specific code.

Scope:
- Add `docs/image-to-3d.md`.
- Define local provider and cloud provider interface.
- Document expected inputs, outputs, costs, GPU/API-key requirements, and limitations.
- Keep default behavior offline/safe.

Verify:
- Docs explain provider setup and limitations clearly.
- Validation passes.

Commit:
`Document image-to-3D integration plan`

### 66. v1.4.1 Image-To-3D Job Schema

Status: completed

Goal:
Add a job file format for image-to-3D generation requests.

Scope:
- Add JSON schema/examples for image path, provider, prompt, output path, quality, and import options.
- Add validation for examples.

Verify:
- Job examples validate.
- Validation passes.

Commit:
`Add image-to-3D job schema`

### 67. v1.4.2 Local Image-To-3D Provider Stub

Status: completed

Goal:
Add a safe local provider interface without requiring heavy model dependencies.

Scope:
- Add provider stub that explains missing setup and expected command.
- Support configurable executable/command path.
- Do not bundle large AI models.

Verify:
- Missing-provider error is actionable.
- Validation passes.

Commit:
`Add local image-to-3D provider stub`

### 68. v1.4.3 Cloud Image-To-3D Provider Adapter

Status: completed

Goal:
Add optional cloud-provider adapter pattern for image-to-3D.

Scope:
- Add provider interface and one documented placeholder adapter.
- Use env vars for API keys.
- Avoid committing secrets.
- Add dry-run mode.

Verify:
- Dry-run works without API key.
- Validation passes.

Commit:
`Add cloud image-to-3D adapter pattern`

### 69. v1.4.4 Image-To-3D Import Workflow

Status: completed

Goal:
Import generated `.glb`/`.obj` output back into Blender automatically.

Scope:
- Add command that runs provider, waits for output, imports model, fits bounds, sets camera, and renders preview.
- Add example job.

Verify:
- Workflow works with a local sample/mock generated model.
- Validation passes.

Commit:
`Add image-to-3D import workflow`

### 70. v1.5.0 Texture Generation Plan

Status: completed

Goal:
Define how generated or user-provided textures should enter the Blender workflow.

Scope:
- Add docs for texture sources, generated maps, naming, and storage.
- Explain offline/manual/cloud options.
- Link from README.

Verify:
- Docs are linked.
- Validation passes.

Commit:
`Document texture generation workflow`

### 71. v1.5.1 Procedural Texture Generator

Status: completed

Goal:
Generate simple local bitmap textures without external AI dependencies.

Scope:
- Add script/action to create wood, fabric, stone, noise, and stripe basecolor textures.
- Save under `assets/textures/` or ignored generated texture folder.
- Add examples.

Verify:
- Generated textures can be applied to an object.
- Validation passes.

Commit:
`Add procedural texture generator`

### 72. v1.5.2 Material Recipe System

Status: completed

Goal:
Create reusable material recipes that combine texture maps and shader settings.

Scope:
- Add material recipe JSON format.
- Add apply-material-recipe action.
- Include wood, fabric, metal, glass, plastic recipes.

Verify:
- Recipe example applies to an object.
- Validation passes.

Commit:
`Add material recipe system`

### 73. v1.5.3 Texture From Image Workflow

Status: completed

Goal:
Improve workflow for user-provided image textures.

Scope:
- Add helper to copy/register user texture images.
- Add guidance for scale/projection tuning.
- Add example applying a user texture to a generated model.

Verify:
- Example applies texture and renders.
- Validation passes.

Commit:
`Add user texture registration workflow`

### 74. v1.6.0 Render Comparison Plan

Status: completed

Goal:
Design a better reference-vs-render comparison loop.

Scope:
- Add docs for reference image, camera, render, compare, adjust loop.
- Define comparison output folder and naming.
- Link from README.

Verify:
- Docs are linked.
- Validation passes.

Commit:
`Document render comparison loop`

### 75. v1.6.1 Side-By-Side Contact Sheet

Status: completed

Goal:
Generate a side-by-side comparison image from reference and render files.

Scope:
- Add script to create contact sheet PNG.
- Support labels and simple metadata.
- Add example command.

Verify:
- Contact sheet generates from existing sample images.
- Validation passes.

Commit:
`Add render comparison contact sheet`

### 76. v1.6.2 Basic Image Difference Metrics

Status: completed

Goal:
Provide simple numeric feedback for reference matching.

Scope:
- Add lightweight image comparison script.
- Compute dimensions, rough color histogram difference, and optional crop support.
- Avoid pretending it is semantic accuracy.

Verify:
- Metrics script runs on sample render/reference.
- Validation passes.

Commit:
`Add basic render comparison metrics`

### 77. v1.6.3 Iteration Report

Status: completed

Goal:
Create a report after reference matching iterations.

Scope:
- Add script/action that records commands, renders, comparison sheets, and notes.
- Save report under ignored generated folder.
- Add docs.

Verify:
- Report script runs.
- Validation passes.

Commit:
`Add render iteration report`

### 78. v1.7.0 GitHub Release Checklist

Status: completed

Goal:
Prepare repeatable GitHub release publishing.

Scope:
- Add `docs/github-release.md`.
- Include branch, tag, push, release notes, and ZIP asset checklist.
- Mention do not publish without user confirmation.

Verify:
- Docs are linked.
- Validation passes.

Commit:
`Document GitHub release workflow`

### 79. v1.7.1 Release Asset Verification

Status: pending

Goal:
Verify ZIP release asset before publishing.

Scope:
- Add script/check for ZIP filename, contents, version, and size.
- Optionally compute SHA256.
- Document output.

Verify:
- Script verifies `dist/codex_blender_addon_v<VERSION>.zip`.
- Validation passes.

Commit:
`Add release asset verification`

### 80. v1.7.2 GitHub Release Draft Helper

Status: pending

Goal:
Prepare release metadata without publishing automatically.

Scope:
- Add script or docs to generate release title/body from release notes.
- Include ZIP path and checksum.
- Keep actual GitHub publish manual/user-confirmed.

Verify:
- Draft metadata generates.
- Validation passes.

Commit:
`Add GitHub release draft helper`

### 81. v1.7.3 Publish GitHub Release

Status: pending

Goal:
Publish GitHub release only when the user explicitly confirms.

Scope:
- Push branch and tag when requested.
- Create GitHub release with ZIP asset when requested.
- Confirm release URL.

Verify:
- GitHub release exists.
- ZIP asset is attached.
- Git status is clean.

Commit:
`Publish GitHub release`
