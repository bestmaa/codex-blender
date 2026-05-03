# Asset Library Manifest

`assets/library.json` is the searchable local asset index for models, textures, and reference images.

## Folders

Use these stable folders for assets that should be searchable and reusable:

- `assets/models/` for `.glb`, `.gltf`, `.fbx`, `.obj`, and other importable model files.
- `assets/textures/` for image textures such as base color, roughness, normal, metallic, and alpha maps.
- `assets/references/` for stable reference images used in examples, docs, or repeatable workflows.

Keep one-off experiments in ignored development folders such as `assets/references/dev/`. Generated renders, exports, scenes, and development-only reference files should not be listed in the stable manifest.

## Manifest Entries

Each asset entry must include:

- `id`: stable machine-readable id.
- `name`: human-readable name.
- `type`: `model`, `texture`, or `reference`.
- `tags`: searchable labels.
- `path`: project-relative path to the asset.
- `scale_hints`: unit, default scale, and target size hints for import or placement.
- `license`: license or usage note.
- `source`: where the asset came from.
- `preview_path`: project-relative preview image path.

Use project-relative paths only. Do not use absolute Windows, WSL, or Blender `//` paths in the manifest.

## Previews

Every entry needs a `preview_path`. For images and textures, the preview can be the asset itself. For models, use a small rendered preview image or a generic placeholder such as `assets/icon.png` until a real preview exists.

Preview images should be stable, lightweight, and committed only when they are useful for users. Do not point previews at ignored `renders/` output unless that image has been copied into a stable asset folder.

## Tags

Tags should be short lowercase search terms. Prefer concrete material, object, style, and format words:

- Good: `wood`, `oak`, `chair`, `obj`, `reference`, `basecolor`
- Avoid: vague tags such as `nice`, `misc`, `test`

Include enough tags for `search_assets` to find the entry without guessing the exact file name.

## License And Source

Every asset must record its license or usage note and source. For project-created samples, use a project note such as `Project sample asset`. For third-party assets, include the license name and source URL or vendor name. Do not add assets when the reuse rights are unclear.

## Scale Hints

`scale_hints.default_scale` is used when importing from the manifest unless the command overrides `scale`.

`scale_hints.target_size` is used by `import_asset_from_library` when `fit_to_bounds` is true and no explicit `target_size` is provided. Use `[x, y, z]` in Blender units. For flat textures or references where one axis is not meaningful, use `0.0` for that axis.

## Add A New Asset

1. Put the file in the correct stable asset folder.
2. Add or choose a preview image.
3. Add an entry to `assets/library.json`.
4. Run `python scripts\validate_project.py`.
5. Test discovery with `examples/search_assets.json` or a targeted `search_assets` command.
6. For model assets, test import with `import_asset_from_library`.

Use `search_assets` or the `blender_search_assets` MCP tool to query this manifest by name, type, tag, extension, or general text. Use `import_asset_from_library` or `blender_import_asset_from_library` to import a model entry by id/name/query and apply its scale hints.
