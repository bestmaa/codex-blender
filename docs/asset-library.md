# Asset Library Manifest

`assets/library.json` is the searchable local asset index for models, textures, and reference images.

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

Generated renders, exports, scenes, and development-only reference files should not be listed in the stable manifest.

Use `search_assets` or the `blender_search_assets` MCP tool to query this manifest by name, type, tag, extension, or general text. Use `import_asset_from_library` or `blender_import_asset_from_library` to import a model entry by id/name/query and apply its scale hints.
