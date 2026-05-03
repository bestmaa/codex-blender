# Command Schema

Commands are JSON objects sent to `POST http://127.0.0.1:8765/command`.

```json
{
  "action": "create_room",
  "params": {}
}
```

Successful responses always include `"ok": true`. Failed responses include `"ok": false`, `error`, `errorType`, and usually `hint`.

## Core

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `ping` | none | `{ok, message}` |
| `run_python` | `code` required string | `{ok, stdout}` |

`run_python` executes trusted local Python inside Blender. It is useful for development and diagnostics, not normal scene authoring.

## Scene Creation

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `create_room` | `style="modern_neon"` | `{ok, message, style}` |
| `create_outdoor_scene` | `road_length=32`, `road_width=5`, `tree_count=12`, `street_light_count=6`, `style="clean_suburban"` | `{ok, message, style, road_length, road_width, tree_count, street_light_count}` |
| `create_furniture_set` | `table_length=3.2`, `table_width=1.55`, `chair_count=4`, `include_plant=true`, `include_lamp=true`, `style="compact_dining"` | `{ok, message, style, table_length, table_width, chair_count, include_plant, include_lamp}` |
| `create_room_layout` | `preset="living_room"`, `style="clean_modern"`; presets: `studio`, `living_room`, `office`, `gallery` | `{ok, message, preset, style}` |
| `create_scene_from_reference` | `title="reference scene"`, optional `floor_color`, `wall_color`, `camera_location`, `target`, `objects=[]` | `{ok, message, title, objects}` |

## Reusable Models

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `create_table_model` | `length=3.6`, `width=2.0`, `height=1.55`, `top_thickness=0.24`, `corner_roundness=0.14`, `include_grain=true`, `wood_color=[0.78,0.47,0.25,1]`, `style="modern_wood"` | `{ok, message, style, length, width, height}` |
| `create_chair_model` | `width=1.35`, `depth=1.25`, `height=2.25`, `seat_height=0.95`, `cushion_thickness=0.18`, `wood_color`, `fabric_color`, `style="modern_wood"` | `{ok, message, style, width, depth, height}` |
| `create_sofa_model` | `width=3.2`, `depth=1.35`, `height=1.55`, `seat_height=0.62`, `cushion_count=3`, `cushion_gap=0.035`, `fabric_color`, `leg_color`, `style="modern_couch"` | `{ok, message, style, width, depth, height}` |
| `create_plant_model` | `height=2.1`, `pot_radius=0.42`, `pot_height=0.58`, `leaf_count=18`, `stem_count=5`, `leaf_color`, `pot_color`, `style="indoor_potted"` | `{ok, message, style, height, leaf_count, stem_count}` |
| `create_lamp_model` | `lamp_type="floor"`, `height`, `shade_radius`, `power=520`, `metal_color`, `shade_color`, `style="warm_modern"`; types: `floor`, `table`, `ceiling_panel` | `{ok, message, style, lamp_type, height, power}` |

## Assets And Imports

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `list_assets` | optional `type`, optional `extension`; types: `model`, `texture`, `reference` | `{ok, message, assets, count}` |
| `import_asset` | `path` required, `location=[0,0,0]`, `rotation=[0,0,0]`, `scale=1.0`; supports `.glb`, `.gltf`, `.fbx`, `.obj` | `{ok, message, path, objects}` |
| `fit_object_to_bounds` | `object` required, `target_size=[1,1,1]`, `target_location=[0,0,0]`, `align_to_floor=true` | `{ok, message, object, dimensions, location}` |

## Scene Inspection And Editing

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `inspect_scene` | `include_hidden=false`, optional `type` such as `MESH`, `LIGHT`, `CAMERA` | `{ok, message, objects, count}` |
| `transform_object` | `object` required, optional `location`, `rotation`, `scale`, `dimensions` | `{ok, message, object, location, rotation, scale, dimensions}` |
| `duplicate_object` | `object` required, `count=3`, `offset=[1,0,0]`, optional `name_prefix` | `{ok, message, source, objects, count, offset}` |
| `animate_object` | `object` required, `frame_start=1`, `frame_end=80`, optional `location_start`, `location_end`, `rotation_start`, `rotation_end`, `scale_start`, `scale_end` | `{ok, message, object, channels, frame_start, frame_end}` |
| `inspect_rig` | none | `{ok, armatures}` |

## Materials And Textures

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `apply_texture_material` | `object` required, `path` or `base_color_path`, optional `roughness_path`, `normal_path`, `metallic_path`, `alpha_path`, `material_name`, `roughness=0.55`, `metallic=0.0`, `opacity=1.0`, `texture_scale=[1,1]`, `texture_offset=[0,0]`, `texture_rotation=0.0`, `projection="uv"`, `mode="replace"` | `{ok, message, object, material, maps, path, projection, texture_scale, texture_offset, texture_rotation, mode}` |
| `apply_material_preset` | `object` required, `preset` required, optional `material_name`, `mode="replace"`; presets: `wood_oak`, `fabric_soft`, `brushed_metal`, `glass_clear`, `matte_plastic` | `{ok, message, object, material, preset, mode}` |

## Reference And Camera

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `add_reference_image` | `path` required, `name="reference image"`, `location=[0,2.2,1.4]`, `rotation=[1.5708,0,0]`, optional `width`, optional `height`, `opacity=0.85`, `unlit=true` | `{ok, message, object, path, width, height, opacity}` |
| `setup_reference_camera` | optional `reference_object`, `camera_location=[4.2,-5.4,2.45]`, `target=[0,0,1.1]`, `lens=32`, `resolution=[1280,720]`, `create_target=true` | `{ok, message, camera, target, resolution}` |
| `setup_compare_view` | `reference_object` required, `mode="side_by_side"`, `reference_location=[2.25,2.15,1.55]`, `reference_width=2.5`, `camera_location=[4.8,-5.8,2.65]`, `target=[0.55,0.55,1.25]`, `lens=30`, `resolution=[1280,720]` | `{ok, message, reference_object, mode, camera, resolution}` |

## Render, Save, Export

| Action | Params And Defaults | Success Shape |
| --- | --- | --- |
| `set_render_preset` | `preset="preview"`; presets: `draft`, `preview`, `final` | `{ok, message, preset, engine, resolution, samples, view_transform, look}` |
| `render_scene` | `output="renders/render.png"`, `resolution=[1280,720]`, optional `samples`, optional `timeout_seconds` for the HTTP wait | `{ok, message, output, resolution}` |
| `save_blend` | `output="scenes/scene.blend"` | `{ok, message, output}` |
| `export_glb` | `output="exports/scene.glb"`, `selected_only=false`, `include_materials=true` | `{ok, message, output, selected_only, include_materials}` |
| `export_obj` | `output="exports/scene.obj"`, `selected_only=false` | `{ok, message, output, selected_only}` |

## Path Rules

Project-relative paths are recommended:

```json
{
  "action": "import_asset",
  "params": {
    "path": "assets/models/sample_pyramid.obj"
  }
}
```

The bridge normalizes paths for references, textures, imports, renders, scenes, and exports. More detail is in `docs/windows-paths.md`.
