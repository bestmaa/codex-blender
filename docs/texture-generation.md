# Texture Generation Workflow

Codex Blender treats textures as local assets first. Generated textures, user-provided images, and cloud-created maps should all enter the same folder and naming workflow before they are applied in Blender.

## Goals

- Keep texture files organized and repeatable.
- Support user-provided images, local procedural generation, and optional cloud generation.
- Make generated maps easy to apply through `apply_texture_material`.
- Avoid committing secrets, paid-service config, or large temporary outputs.

## Storage

Stable texture assets should live under:

```text
assets/textures/
```

Temporary generated outputs should live under an ignored generated folder until the user decides to keep them:

```text
assets/textures/generated/
```

Use project-relative paths in commands and manifests. Absolute Windows or WSL paths are okay for one-off local use, but project-relative paths are easier to share.

## Naming

Use one asset prefix plus a map suffix:

```text
oak_table_basecolor.png
oak_table_roughness.png
oak_table_normal.png
oak_table_metallic.png
oak_table_alpha.png
```

Recommended suffixes:

- `basecolor` or `albedo`: visible color.
- `roughness`: surface shine control.
- `normal`: small bump detail without changing geometry.
- `metallic`: metalness mask.
- `alpha`: transparency mask.
- `height`: displacement source for later manual workflows.

Prefer lowercase names with hyphens or underscores. Avoid spaces in asset filenames.

## Sources

User-provided textures:

- Put the original image under `assets/textures/` when it is stable.
- Record source/license notes in `assets/library.json` if it becomes a reusable asset.
- Use `texture_scale`, `texture_offset`, `texture_rotation`, and `projection` to tune placement.

Use the registration helper when a user gives an image outside the project:

```powershell
python scripts\register_user_texture.py C:\path\to\fabric.png --name "Blue Fabric" --asset-id blue_fabric --destination assets\textures\blue_fabric_basecolor.png --register
```

Preview the copy/library update first:

```powershell
python scripts\register_user_texture.py assets\textures\oak_wood_basecolor.png --name "Registered Oak Wood User Texture" --asset-id registered_oak_wood_user_texture --destination assets\textures\generated\registered_oak_wood_user_texture.png --dry-run
```

After registration or copy, apply the image with `apply_texture_material`. For generated/imported models, inspect the scene first and use the exact imported object name.

Offline/manual textures:

- Create simple bitmap patterns locally for blockouts.
- Use external tools such as Blender, Krita, GIMP, Material Maker, or Substance workflows outside this repository.
- Save finished maps into `assets/textures/`.

Local procedural textures:

```powershell
python scripts\generate_procedural_texture.py wood assets\textures\generated\procedural_wood_basecolor.png --width 512 --height 512 --seed 71
```

Supported local texture kinds:

- `wood`
- `fabric`
- `stone`
- `noise`
- `stripes`

The generator writes PNG basecolor textures and uses only Python's standard library. Use it for blockout materials, quick reference matching, or creating a starting image before manual editing.

Cloud or AI-generated textures:

- Use explicit user configuration before uploading any source image.
- Store API keys only in environment variables.
- Save generated files locally before applying them in Blender.
- Review provider terms for commercial use and output ownership.

## Applying Maps

Use `apply_texture_material` for one image or a PBR-style set:

```json
{
  "action": "apply_texture_material",
  "params": {
    "object": "tabletop",
    "base_color_path": "assets/textures/oak_table_basecolor.png",
    "roughness_path": "assets/textures/oak_table_roughness.png",
    "normal_path": "assets/textures/oak_table_normal.png",
    "material_name": "oak tabletop",
    "texture_scale": [1.0, 1.0],
    "texture_offset": [0.0, 0.0],
    "texture_rotation": 0.0,
    "projection": "uv",
    "mode": "replace"
  }
}
```

For quick blockouts, use `apply_material_preset` first, then replace it with texture maps after the model shape and camera are acceptable.

Reusable material recipes live in:

```text
assets/material_recipes.json
```

Use `apply_material_recipe` when the material should carry both shader settings and optional map paths:

```json
{
  "action": "apply_material_recipe",
  "params": {
    "object": "tabletop",
    "recipe": "wood_warm",
    "material_name": "warm wood tabletop",
    "texture_scale": [2.0, 1.0],
    "projection": "generated",
    "mode": "replace"
  }
}
```

## Quality Loop

1. Apply a draft texture with rough scale and projection.
2. Render a preview.
3. Compare against the reference image.
4. Adjust UV/projection, scale, rotation, color, and roughness.
5. Promote useful maps from `assets/textures/generated/` to `assets/textures/`.
6. Add library metadata only for assets worth reusing.

## Limits

Texture generation does not fix poor geometry, bad UVs, or incorrect lighting. If the render still looks wrong after texture tuning, inspect model proportions, camera framing, material roughness, and light placement before generating more maps.
