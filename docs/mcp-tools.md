# MCP Tool Coverage

The MCP server in `scripts/codex_blender_mcp.py` exposes stable tools for normal bridge workflows. Each tool calls the local Blender bridge at `http://127.0.0.1:8765`.

## Coverage

| Bridge Action | MCP Tool |
| --- | --- |
| `ping` | `blender_health` |
| `create_room` | `blender_create_room` |
| `create_outdoor_scene` | `blender_create_outdoor_scene` |
| `create_table_model` | `blender_create_table_model` |
| `create_primitive` | `blender_create_primitive` |
| `create_furniture_preset` | `blender_create_furniture_preset` |
| `create_architecture_preset` | `blender_create_architecture_preset` |
| `create_chair_model` | `blender_create_chair_model` |
| `create_sofa_model` | `blender_create_sofa_model` |
| `create_plant_model` | `blender_create_plant_model` |
| `create_lamp_model` | `blender_create_lamp_model` |
| `create_furniture_set` | `blender_create_furniture_set` |
| `create_room_layout` | `blender_create_room_layout` |
| `list_procedural_catalog` | `blender_list_procedural_catalog` |
| `list_assets` | `blender_list_assets` |
| `fit_object_to_bounds` | `blender_fit_object_to_bounds` |
| `inspect_scene` | `blender_inspect_scene` |
| `transform_object` | `blender_transform_object` |
| `duplicate_object` | `blender_duplicate_object` |
| `animate_object` | `blender_animate_object` |
| `set_render_preset` | `blender_set_render_preset` |
| `save_blend` | `blender_save_blend` |
| `export_glb` | `blender_export_glb` |
| `export_obj` | `blender_export_obj` |
| `import_asset` | `blender_import_asset` |
| `add_reference_image` | `blender_add_reference_image` |
| `apply_texture_material` | `blender_apply_texture_material` |
| `apply_material_preset` | `blender_apply_material_preset` |
| `setup_reference_camera` | `blender_setup_reference_camera` |
| `setup_compare_view` | `blender_setup_compare_view` |
| `create_scene_from_reference` | `blender_create_scene_from_reference` |
| `render_scene` | `blender_render_scene` |
| `inspect_rig` | `blender_inspect_rig` |

## Compatibility Tool

`blender_blendermcp_command` accepts a common BlenderMCP-style payload, translates it to a native Codex Blender bridge payload, and runs it.

Example:

```json
{
  "payload": {
    "tool": "get_scene_info",
    "params": {
      "include_hidden": false
    }
  }
}
```

Prefer native tools for normal Codex Blender workflows. Use `blender_blendermcp_command` when reusing prompts or payloads written for BlenderMCP-style tools. Unsupported compatibility payloads return `UnsupportedCompatibilityPayload` instead of silently running unsafe commands.

## Raw-Only Action

`run_python` is intentionally not exposed as a first-class MCP tool because it executes arbitrary Python inside Blender. Trusted local callers can still send it through `blender_command` when development diagnostics require it.

## Raw Command Fallback

`blender_command` accepts a complete trusted JSON payload:

```json
{
  "action": "inspect_scene",
  "params": {
    "include_hidden": false
  }
}
```

Use first-class tools for stable workflows. Use `blender_command` only for raw payloads, development-only actions, or newly added actions before the MCP server has a dedicated tool.
