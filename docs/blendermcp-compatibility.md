# BlenderMCP Compatibility Plan

This project has its own bridge command schema and MCP tools. BlenderMCP compatibility means accepting common BlenderMCP-style tool/payload names and translating the safe subset into Codex Blender native actions.

Compatibility is an adapter, not a replacement. Native actions remain the preferred stable API because they are validated, documented, and covered by project examples.

## Public Tool Families Reviewed

Common public BlenderMCP listings and docs show these recurring tool families:

- Scene inspection: `get_scene_info`
- Object inspection: `get_object_info`
- Object creation: `create_object`, `blender_object_create`
- Object deletion: `delete_object`
- Object modification: `modify_object`
- Material updates: `apply_material`
- Python execution: `execute_blender_code`
- Asset downloads: Poly Haven tools such as `download_polyhaven_asset`
- AI model generation: Hyper3D/Hunyuan/Tripo-style image/text-to-3D tools

References:

- Glama BlenderMCP tool listing for `get_scene_info`: https://glama.ai/mcp/servers/%40ahujasid/blender-mcp/tools/get_scene_info
- Glama BlenderMCP tool listing for `get_object_info`: https://glama.ai/mcp/servers/%40wenyen-hsu/blender-mcp/tools/get_object_info
- Playbooks Blender MCP overview listing `create_object`, `delete_object`, `modify_object`, `apply_material`, and `execute_blender_code`: https://playbooks.com/mcp/mikeysrecipes/blender-mcp
- PyPI `blender-mcp-server` tool reference listing `blender_scene_get_info` and `blender_object_create`: https://pypi.org/project/blender-mcp-server/

## Compatibility Levels

### Level 1: Direct Mapping

These can map to existing Codex Blender actions with little or no new bridge behavior.

| BlenderMCP-style Tool Or Payload | Native Action Or MCP Tool | Notes |
| --- | --- | --- |
| `get_scene_info` | `inspect_scene` / `blender_inspect_scene` | Use `include_hidden=false` by default. |
| `blender_scene_get_info` | `inspect_scene` / `blender_inspect_scene` | Alias for scene inspection. |
| `get_object_info` | `inspect_scene` then filter by object name | Native bridge does not yet have a dedicated single-object action. |
| `render` / `render_scene` | `render_scene` / `blender_render_scene` | Existing native action. |
| `save_scene` / `save_blend` | `save_blend` / `blender_save_blend` | Existing native action. |
| `import_asset` | `import_asset` / `blender_import_asset` | Existing native action. |
| `export_glb` | `export_glb` / `blender_export_glb` | Existing native action. |
| `export_obj` | `export_obj` / `blender_export_obj` | Existing native action. |
| `apply_material` with preset-like params | `apply_material_preset` | Works for supported presets only. |
| `apply_material` with image texture params | `apply_texture_material` | Works when an image path is provided. |
| `execute_blender_code` | `run_python` through `blender_command` | Trusted local development only. |

### Level 2: Partial Mapping With New Helpers

These need small native bridge additions before compatibility is useful.

| BlenderMCP-style Tool Or Payload | Needed Native Helper |
| --- | --- |
| `create_object` with primitive types | Generic `create_primitive` action for cube, sphere, cylinder, cone, plane, torus, text. |
| `blender_object_create` | Same generic primitive helper. |
| `modify_object` | Existing `transform_object` covers transforms, but material and visibility fields need separate handling. |
| `delete_object` | New safe `delete_object` action with exact-name matching. |
| `set_camera` / camera placement payloads | Existing `setup_reference_camera` covers reference flows; a generic `set_camera` helper would improve compatibility. |
| `create_light` / light controls | New generic `create_light` and `modify_light` actions. |
| `create_material` | Existing presets/textures cover common cases; arbitrary material creation needs a recipe/generic material action. |

### Level 3: Workflow Mapping

These are larger workflows and should map to planned post-v1 systems instead of one small adapter.

| BlenderMCP-style Tool Family | Planned Codex Blender Work |
| --- | --- |
| Poly Haven download/import | Asset library search/import workflow (`v1.3.x`). |
| Hyper3D/Hunyuan/Tripo image-to-3D | Image-to-3D provider interface (`v1.4.x`). |
| Generated texture/material workflows | Texture generation and material recipes (`v1.5.x`). |
| Reference-vs-render quality loops | Render comparison loop (`v1.6.x`). |

### Unsupported In First Adapter

The first compatibility adapter should return clear `UnsupportedCompatibilityPayload` errors for:

- destructive scene-wide operations that do not have a native safety wrapper
- arbitrary modifier stacks
- geometry nodes
- physics simulation
- rig editing
- remote asset downloads
- cloud image-to-3D generation
- any command that requires secrets, paid APIs, or large external model downloads

## Proposed Payload Shapes

The adapter should accept at least these shapes:

```json
{
  "tool": "get_scene_info",
  "params": {}
}
```

```json
{
  "name": "create_object",
  "arguments": {
    "type": "cube",
    "name": "sample cube",
    "location": [0, 0, 1],
    "scale": [1, 1, 1]
  }
}
```

```json
{
  "command": "render_scene",
  "args": {
    "output": "renders/compatibility.png"
  }
}
```

The adapter should normalize `tool`, `name`, `command`, `params`, `arguments`, and `args` into a native bridge payload:

```json
{
  "action": "inspect_scene",
  "params": {}
}
```

## Terminal Example

The terminal bridge can translate compatibility examples before sending them to Blender:

```powershell
python bridge\codex_blender_bridge.py examples\blendermcp\get_scene_info.json
python bridge\codex_blender_bridge.py examples\blendermcp\create_cube.json
python bridge\codex_blender_bridge.py examples\blendermcp\render_scene.json
python bridge\codex_blender_bridge.py examples\blendermcp\save_scene.json
```

The same sequence can be run as an optional live smoke test when Blender is open and the bridge is running:

```powershell
python scripts\smoke_test_blendermcp.py
```

## MCP Example

Use the compatibility MCP tool when a prompt or saved payload uses BlenderMCP-style naming:

```json
{
  "payload": {
    "name": "create_object",
    "arguments": {
      "type": "cube",
      "name": "compatibility cube",
      "location": [0, 0, 0.75],
      "dimensions": [1.5, 1.5, 1.5]
    }
  }
}
```

## Implementation Plan

1. Add a pure Python adapter function that converts supported BlenderMCP-style payloads to native bridge payloads.
2. Add examples under `examples/blendermcp/`.
3. Add validation for compatibility examples.
4. Add an MCP wrapper tool after the adapter is tested.
5. Add live smoke tests after primitive helpers exist.

## Success Criteria

- Safe inspection, render, save, import, material, and transform payloads translate predictably.
- Unsupported payloads return actionable errors instead of silently running arbitrary code.
- Compatibility docs clearly distinguish direct mappings, partial mappings, workflow mappings, and unsupported families.
