#!/usr/bin/env python3
"""Validate the Codex Blender project without launching Blender."""

from __future__ import annotations

import json
import importlib.util
import py_compile
import re
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    ".codex-plugin/plugin.json",
    ".mcp.json",
    "README.md",
    "LICENSE",
    "blender_addon/codex_blender_addon.py",
    "bridge/codex_blender_bridge.py",
    "bridge/blendermcp_adapter.py",
    "scripts/codex_blender_mcp.py",
    "scripts/image_to_3d_adapters.py",
    "scripts/run_image_to_3d_job.py",
    "scripts/run_image_to_3d_import_workflow.py",
    "scripts/generate_procedural_texture.py",
    "scripts/register_user_texture.py",
    "scripts/package_addon.py",
    "scripts/smoke_test_bridge.py",
    "scripts/smoke_test_blendermcp.py",
    "skills/blender/SKILL.md",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/render_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/create_primitive_library.json",
    "examples/create_furniture_presets.json",
    "examples/create_architecture_presets.json",
    "examples/list_procedural_catalog.json",
    "examples/create_chair_model.json",
    "examples/create_sofa_model.json",
    "examples/create_plant_model.json",
    "examples/create_lamp_model.json",
    "examples/create_furniture_set.json",
    "examples/create_room_layout.json",
    "examples/list_assets.json",
    "examples/search_assets.json",
    "examples/fit_sample_asset.json",
    "examples/inspect_scene.json",
    "examples/transform_tabletop.json",
    "examples/duplicate_table_leg.json",
    "examples/animate_tabletop.json",
    "examples/set_render_preset.json",
    "examples/add_reference_image.json",
    "examples/apply_table_texture.json",
    "examples/apply_scaled_wood_texture.json",
    "examples/apply_multimap_wood_texture.json",
    "examples/apply_material_preset.json",
    "examples/apply_material_recipe.json",
    "examples/apply_user_texture_to_generated_model.json",
    "examples/setup_reference_camera.json",
    "examples/setup_compare_view.json",
    "examples/export_table_glb.json",
    "examples/export_table_obj.json",
    "examples/import_asset.json",
    "examples/import_asset_from_library.json",
    "examples/create_scene_from_reference.json",
    "examples/render_scene.json",
    "examples/render_user_texture_model.json",
    "examples/save_blend.json",
    "examples/inspect_rig.json",
    "examples/blendermcp/get_scene_info.json",
    "examples/blendermcp/create_cube.json",
    "examples/blendermcp/render_scene.json",
    "examples/blendermcp/save_scene.json",
    "examples/blendermcp/unsupported_delete_object.json",
    "assets/models/sample_pyramid.obj",
    "assets/library.json",
    "assets/material_recipes.json",
    "docs/asset-library.md",
    "docs/image-to-3d.md",
    "docs/texture-generation.md",
    "docs/render-comparison.md",
    "schemas/image-to-3d-job.schema.json",
    "examples/image-to-3d/local_provider_job.json",
    "examples/image-to-3d/cloud_placeholder_job.json",
    "examples/image-to-3d/mock_import_workflow_job.json",
    "examples/textures/generate_wood_texture.json",
    "examples/textures/register_user_texture.json",
    "docs/quickstart-demo.md",
    "docs/commands.md",
    "docs/mcp-tools.md",
    "docs/blendermcp-compatibility.md",
    "docs/reference-workflow.md",
    "docs/troubleshooting.md",
    "docs/windows-paths.md",
    "docs/release-packaging.md",
    "docs/release-notes-v1.md",
    "docs/known-limitations.md",
    "docs/demo-assets.md",
    "docs/smoke-test-matrix.md",
    "docs/final-user-walkthrough.md",
]

PYTHON_FILES = [
    "blender_addon/codex_blender_addon.py",
    "bridge/codex_blender_bridge.py",
    "bridge/blendermcp_adapter.py",
    "scripts/codex_blender_mcp.py",
    "scripts/image_to_3d_adapters.py",
    "scripts/run_image_to_3d_job.py",
    "scripts/run_image_to_3d_import_workflow.py",
    "scripts/generate_procedural_texture.py",
    "scripts/register_user_texture.py",
    "scripts/package_addon.py",
    "scripts/smoke_test_bridge.py",
    "scripts/smoke_test_blendermcp.py",
    "scripts/validate_project.py",
]

JSON_FILES = [
    ".codex-plugin/plugin.json",
    ".mcp.json",
    ".agents/plugins/marketplace.json",
    "assets/library.json",
    "assets/material_recipes.json",
    "schemas/image-to-3d-job.schema.json",
    "examples/image-to-3d/local_provider_job.json",
    "examples/image-to-3d/cloud_placeholder_job.json",
    "examples/image-to-3d/mock_import_workflow_job.json",
    "examples/textures/generate_wood_texture.json",
    "examples/textures/register_user_texture.json",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/render_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/create_primitive_library.json",
    "examples/create_furniture_presets.json",
    "examples/create_architecture_presets.json",
    "examples/list_procedural_catalog.json",
    "examples/create_chair_model.json",
    "examples/create_sofa_model.json",
    "examples/create_plant_model.json",
    "examples/create_lamp_model.json",
    "examples/create_furniture_set.json",
    "examples/create_room_layout.json",
    "examples/list_assets.json",
    "examples/search_assets.json",
    "examples/fit_sample_asset.json",
    "examples/inspect_scene.json",
    "examples/transform_tabletop.json",
    "examples/duplicate_table_leg.json",
    "examples/animate_tabletop.json",
    "examples/set_render_preset.json",
    "examples/add_reference_image.json",
    "examples/apply_table_texture.json",
    "examples/apply_scaled_wood_texture.json",
    "examples/apply_multimap_wood_texture.json",
    "examples/apply_material_preset.json",
    "examples/apply_material_recipe.json",
    "examples/apply_user_texture_to_generated_model.json",
    "examples/setup_reference_camera.json",
    "examples/setup_compare_view.json",
    "examples/export_table_glb.json",
    "examples/export_table_obj.json",
    "examples/import_asset.json",
    "examples/import_asset_from_library.json",
    "examples/create_scene_from_reference.json",
    "examples/render_scene.json",
    "examples/render_user_texture_model.json",
    "examples/save_blend.json",
    "examples/inspect_rig.json",
]


def project_path(relative_path: str) -> Path:
    return ROOT / relative_path


def check_required_files() -> None:
    missing = [path for path in REQUIRED_FILES if not project_path(path).exists()]
    if missing:
        raise AssertionError("Missing required files: " + ", ".join(missing))


def check_python_syntax() -> None:
    for relative_path in PYTHON_FILES:
        py_compile.compile(project_path(relative_path), doraise=True)


def check_json_files() -> None:
    stable_examples = sorted(f"examples/{path.name}" for path in (ROOT / "examples").glob("*.json"))
    for relative_path in sorted(set(JSON_FILES + stable_examples)):
        json.loads(project_path(relative_path).read_text(encoding="utf-8"))


def check_versions() -> None:
    manifest = json.loads(project_path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    addon_source = project_path("blender_addon/codex_blender_addon.py").read_text(encoding="utf-8")
    mcp_source = project_path("scripts/codex_blender_mcp.py").read_text(encoding="utf-8")
    expected = tuple(int(part) for part in version.split("."))
    if f'"version": {expected}' not in addon_source:
        raise AssertionError(f"Add-on bl_info version does not match plugin version {version}")
    if f'"version": "{version}"' not in mcp_source:
        raise AssertionError(f"MCP server version does not match plugin version {version}")


def check_version_references() -> None:
    manifest = json.loads(project_path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    readme = project_path("README.md").read_text(encoding="utf-8")
    expected_zip = f"codex_blender_addon_v{version}.zip"
    if expected_zip not in readme:
        raise AssertionError(f"README does not mention current package ZIP {expected_zip}")
    supported_heading = f"Supported v{version} actions"
    prerelease_heading = f"Supported v{version} pre-release actions"
    if supported_heading not in readme and prerelease_heading not in readme:
        raise AssertionError(f"README supported-action version does not match {version}")


def get_supported_actions() -> set[str]:
    addon_source = project_path("blender_addon/codex_blender_addon.py").read_text(encoding="utf-8")
    return set(re.findall(r'if action == "([^"]+)"', addon_source))


def check_examples() -> None:
    expected_actions = {
        "examples/create_room.json": "create_room",
        "examples/create_outdoor_scene.json": "create_outdoor_scene",
        "examples/render_outdoor_scene.json": "render_scene",
        "examples/create_table_model.json": "create_table_model",
        "examples/create_primitive_library.json": "create_primitive",
        "examples/create_furniture_presets.json": "create_furniture_preset",
        "examples/create_architecture_presets.json": "create_architecture_preset",
        "examples/list_procedural_catalog.json": "list_procedural_catalog",
        "examples/create_chair_model.json": "create_chair_model",
        "examples/create_sofa_model.json": "create_sofa_model",
        "examples/create_plant_model.json": "create_plant_model",
        "examples/create_lamp_model.json": "create_lamp_model",
        "examples/create_furniture_set.json": "create_furniture_set",
        "examples/create_room_layout.json": "create_room_layout",
        "examples/list_assets.json": "list_assets",
        "examples/search_assets.json": "search_assets",
        "examples/fit_sample_asset.json": "fit_object_to_bounds",
        "examples/inspect_scene.json": "inspect_scene",
        "examples/transform_tabletop.json": "transform_object",
        "examples/duplicate_table_leg.json": "duplicate_object",
        "examples/animate_tabletop.json": "animate_object",
        "examples/set_render_preset.json": "set_render_preset",
        "examples/add_reference_image.json": "add_reference_image",
        "examples/apply_table_texture.json": "apply_texture_material",
        "examples/apply_scaled_wood_texture.json": "apply_texture_material",
        "examples/apply_multimap_wood_texture.json": "apply_texture_material",
        "examples/apply_material_preset.json": "apply_material_preset",
        "examples/apply_material_recipe.json": "apply_material_recipe",
        "examples/apply_user_texture_to_generated_model.json": "apply_texture_material",
        "examples/setup_reference_camera.json": "setup_reference_camera",
        "examples/setup_compare_view.json": "setup_compare_view",
        "examples/export_table_glb.json": "export_glb",
        "examples/export_table_obj.json": "export_obj",
        "examples/import_asset.json": "import_asset",
        "examples/import_asset_from_library.json": "import_asset_from_library",
        "examples/create_scene_from_reference.json": "create_scene_from_reference",
        "examples/render_scene.json": "render_scene",
        "examples/render_user_texture_model.json": "render_scene",
        "examples/save_blend.json": "save_blend",
        "examples/inspect_rig.json": "inspect_rig",
    }
    for relative_path, action in expected_actions.items():
        payload = json.loads(project_path(relative_path).read_text(encoding="utf-8"))
        if payload.get("action") != action:
            raise AssertionError(f"{relative_path} expected action {action}")
    supported_actions = get_supported_actions()
    stable_examples = sorted((ROOT / "examples").glob("*.json"))
    for path in stable_examples:
        payload = json.loads(path.read_text(encoding="utf-8"))
        action = payload.get("action")
        if action not in supported_actions:
            raise AssertionError(f"{path.relative_to(ROOT)} uses unsupported action {action}")


def check_skill_actions() -> None:
    skill = project_path("skills/blender/SKILL.md").read_text(encoding="utf-8")
    example_actions = {
        json.loads(path.read_text(encoding="utf-8")).get("action")
        for path in (ROOT / "examples").glob("*.json")
    }
    missing = sorted(action for action in example_actions if action and action not in skill)
    if missing:
        raise AssertionError("Skill does not mention actions: " + ", ".join(missing))


def check_readme_paths() -> None:
    readme = project_path("README.md").read_text(encoding="utf-8")
    referenced_paths = sorted(set(re.findall(r"(?:examples|docs|assets/models|scripts|bridge|blender_addon)/[\w./-]+", readme)))
    missing = [path for path in referenced_paths if not project_path(path).exists()]
    if missing:
        raise AssertionError("README references missing paths: " + ", ".join(missing))


def check_bridge_path_normalization() -> None:
    bridge_path = project_path("bridge/codex_blender_bridge.py")
    spec = importlib.util.spec_from_file_location("codex_blender_bridge", bridge_path)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load bridge path normalization module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payload = {
        "action": "apply_texture_material",
        "params": {
            "path": "assets/textures/wood.png",
            "base_color_path": "assets/textures/wood_basecolor.png",
            "roughness_path": "assets/textures/wood_roughness.png",
            "normal_path": "assets/textures/wood_normal.png",
            "metallic_path": "assets/textures/wood_metallic.png",
            "alpha_path": "assets/textures/wood_alpha.png",
        },
    }
    normalized = module.normalize_command_paths(payload, ROOT)
    for key in ("path", "base_color_path", "roughness_path", "normal_path", "metallic_path", "alpha_path"):
        value = normalized["params"][key]
        if not Path(value).is_absolute():
            raise AssertionError(f"Texture path was not normalized: {key}")

    for action in ("render_scene", "save_blend", "export_glb", "export_obj"):
        normalized = module.normalize_command_paths({"action": action, "params": {"output": "renders/test.png"}}, ROOT)
        if not Path(normalized["params"]["output"]).is_absolute():
            raise AssertionError(f"Output path was not normalized for {action}")

    for action in ("import_asset", "add_reference_image"):
        normalized = module.normalize_command_paths({"action": action, "params": {"path": "assets/models/sample_pyramid.obj"}}, ROOT)
        if not Path(normalized["params"]["path"]).is_absolute():
            raise AssertionError(f"Input path was not normalized for {action}")


def check_blendermcp_adapter_examples() -> None:
    adapter_path = project_path("bridge/blendermcp_adapter.py")
    spec = importlib.util.spec_from_file_location("blendermcp_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load BlenderMCP adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    expected = {
        "examples/blendermcp/get_scene_info.json": "inspect_scene",
        "examples/blendermcp/create_cube.json": "create_scene_from_reference",
        "examples/blendermcp/render_scene.json": "render_scene",
        "examples/blendermcp/save_scene.json": "save_blend",
    }
    supported_actions = get_supported_actions()
    for relative_path, action in expected.items():
        payload = json.loads(project_path(relative_path).read_text(encoding="utf-8"))
        translated = module.translate_blendermcp_payload(payload)
        if translated.get("action") != action:
            raise AssertionError(f"{relative_path} expected translated action {action}")
        if action not in supported_actions:
            raise AssertionError(f"{relative_path} translates to unsupported action {action}")

    unsupported = module.translate_blendermcp_payload(
        json.loads(project_path("examples/blendermcp/unsupported_delete_object.json").read_text(encoding="utf-8"))
    )
    if unsupported.get("ok") is not False or unsupported.get("errorType") != "UnsupportedCompatibilityPayload":
        raise AssertionError("Unsupported BlenderMCP payload did not return a clear compatibility error")


def check_asset_library_manifest() -> None:
    manifest = json.loads(project_path("assets/library.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0":
        raise AssertionError("Asset library schema_version must be 1.0")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise AssertionError("Asset library must contain a non-empty assets list")

    seen_ids = set()
    allowed_types = {"model", "texture", "reference"}
    required_fields = {"id", "name", "type", "tags", "path", "scale_hints", "license", "source", "preview_path"}
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            raise AssertionError(f"Asset entry {index} must be an object")
        missing = sorted(required_fields - set(asset))
        if missing:
            raise AssertionError(f"Asset entry {index} missing fields: " + ", ".join(missing))
        asset_id = asset["id"]
        if not isinstance(asset_id, str) or not asset_id:
            raise AssertionError(f"Asset entry {index} has invalid id")
        if asset_id in seen_ids:
            raise AssertionError(f"Duplicate asset id: {asset_id}")
        seen_ids.add(asset_id)
        if asset["type"] not in allowed_types:
            raise AssertionError(f"Asset {asset_id} has unsupported type {asset['type']}")
        if not isinstance(asset["tags"], list) or not all(isinstance(tag, str) and tag for tag in asset["tags"]):
            raise AssertionError(f"Asset {asset_id} tags must be non-empty strings")
        for path_key in ("path", "preview_path"):
            value = asset[path_key]
            if not isinstance(value, str) or not value:
                raise AssertionError(f"Asset {asset_id} {path_key} must be a non-empty string")
            if Path(value).is_absolute():
                raise AssertionError(f"Asset {asset_id} {path_key} must be project-relative")
            if not project_path(value).exists():
                raise AssertionError(f"Asset {asset_id} {path_key} does not exist: {value}")
        scale_hints = asset["scale_hints"]
        if not isinstance(scale_hints, dict):
            raise AssertionError(f"Asset {asset_id} scale_hints must be an object")
        if not isinstance(scale_hints.get("default_scale"), (int, float)):
            raise AssertionError(f"Asset {asset_id} scale_hints.default_scale must be numeric")
        target_size = scale_hints.get("target_size")
        if not isinstance(target_size, list) or len(target_size) != 3:
            raise AssertionError(f"Asset {asset_id} scale_hints.target_size must be [x, y, z]")


def check_material_recipes() -> None:
    manifest = json.loads(project_path("assets/material_recipes.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0":
        raise AssertionError("Material recipe schema_version must be 1.0")
    recipes = manifest.get("recipes")
    if not isinstance(recipes, dict) or not recipes:
        raise AssertionError("Material recipe manifest must contain recipes")
    required = {"wood_warm", "fabric_blue", "metal_brushed", "glass_clear", "plastic_matte"}
    missing = sorted(required - set(recipes))
    if missing:
        raise AssertionError("Missing material recipes: " + ", ".join(missing))
    for name, recipe in recipes.items():
        if not isinstance(recipe, dict):
            raise AssertionError(f"Material recipe {name} must be an object")
        color = recipe.get("base_color")
        if not isinstance(color, list) or len(color) != 4:
            raise AssertionError(f"Material recipe {name} base_color must be RGBA")
        for numeric in ("roughness", "metallic", "opacity"):
            if not isinstance(recipe.get(numeric), (int, float)):
                raise AssertionError(f"Material recipe {name} {numeric} must be numeric")
        maps = recipe.get("maps", {})
        if maps:
            if not isinstance(maps, dict):
                raise AssertionError(f"Material recipe {name} maps must be an object")
            for key, value in maps.items():
                if key not in {"path", "base_color_path", "roughness_path", "normal_path", "metallic_path", "alpha_path"}:
                    raise AssertionError(f"Material recipe {name} has unsupported map key {key}")
                if not isinstance(value, str) or not value:
                    raise AssertionError(f"Material recipe {name} map path must be a non-empty string")
                if not project_path(value).exists():
                    raise AssertionError(f"Material recipe {name} map path does not exist: {value}")


def check_image_to_3d_job_examples() -> None:
    schema = json.loads(project_path("schemas/image-to-3d-job.schema.json").read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    allowed_qualities = set(schema["properties"]["quality"]["enum"])
    allowed_model_extensions = {".glb", ".gltf", ".obj", ".fbx"}
    for path in sorted((ROOT / "examples" / "image-to-3d").glob("*.json")):
        job = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(required - set(job))
        if missing:
            raise AssertionError(f"{path.relative_to(ROOT)} missing required fields: " + ", ".join(missing))
        for field in ("provider", "input_image", "output"):
            if not isinstance(job.get(field), str) or not job[field]:
                raise AssertionError(f"{path.relative_to(ROOT)} {field} must be a non-empty string")
        input_image = Path(job["input_image"])
        if not input_image.is_absolute() and not project_path(job["input_image"]).exists():
            raise AssertionError(f"{path.relative_to(ROOT)} input_image does not exist: {job['input_image']}")
        if job["quality"] not in allowed_qualities:
            raise AssertionError(f"{path.relative_to(ROOT)} quality must be one of {sorted(allowed_qualities)}")
        if Path(job["output"]).suffix.lower() not in allowed_model_extensions:
            raise AssertionError(f"{path.relative_to(ROOT)} output must be a supported model extension")
        import_options = job.get("import_options", {})
        if import_options and not isinstance(import_options, dict):
            raise AssertionError(f"{path.relative_to(ROOT)} import_options must be an object")
        provider_command = job.get("provider_command")
        if provider_command is not None:
            if isinstance(provider_command, str):
                if not provider_command:
                    raise AssertionError(f"{path.relative_to(ROOT)} provider_command must not be empty")
            elif isinstance(provider_command, list):
                if not provider_command or not all(isinstance(part, str) and part for part in provider_command):
                    raise AssertionError(f"{path.relative_to(ROOT)} provider_command must be non-empty strings")
            else:
                raise AssertionError(f"{path.relative_to(ROOT)} provider_command must be a string or string list")
        for field in ("provider_adapter", "api_key_env", "endpoint"):
            if field in job and (not isinstance(job[field], str) or not job[field]):
                raise AssertionError(f"{path.relative_to(ROOT)} {field} must be a non-empty string")
        if "mock_output_from" in job:
            if not isinstance(job["mock_output_from"], str) or not job["mock_output_from"]:
                raise AssertionError(f"{path.relative_to(ROOT)} mock_output_from must be a non-empty string")
            mock_path = project_path(job["mock_output_from"])
            if not mock_path.exists():
                raise AssertionError(f"{path.relative_to(ROOT)} mock_output_from does not exist: {job['mock_output_from']}")
        for vector_key in ("location", "rotation", "target_location"):
            value = import_options.get(vector_key)
            if value is not None and (not isinstance(value, list) or len(value) != 3):
                raise AssertionError(f"{path.relative_to(ROOT)} import_options.{vector_key} must be [x, y, z]")
        for vector_key in ("camera_location", "camera_target"):
            value = import_options.get(vector_key)
            if value is not None and (not isinstance(value, list) or len(value) != 3):
                raise AssertionError(f"{path.relative_to(ROOT)} import_options.{vector_key} must be [x, y, z]")
        resolution = import_options.get("resolution")
        if resolution is not None and (not isinstance(resolution, list) or len(resolution) != 2):
            raise AssertionError(f"{path.relative_to(ROOT)} import_options.resolution must be [width, height]")


def check_image_to_3d_provider_stub() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(project_path("scripts/run_image_to_3d_job.py")),
            str(project_path("examples/image-to-3d/local_provider_job.json")),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 2:
        raise AssertionError(f"Provider stub should return setup error code 2, got {completed.returncode}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Provider stub did not return JSON: {exc}") from exc
    if payload.get("errorType") != "MissingImageTo3DProviderCommand":
        raise AssertionError("Provider stub missing-provider error is not actionable")
    if "expected_command" not in payload or "setup" not in payload:
        raise AssertionError("Provider stub setup error must include expected_command and setup")


def check_cloud_image_to_3d_adapter() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(project_path("scripts/run_image_to_3d_job.py")),
            str(project_path("examples/image-to-3d/cloud_placeholder_job.json")),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Cloud adapter dry-run failed with code {completed.returncode}: {completed.stderr}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Cloud adapter dry-run did not return JSON: {exc}") from exc
    if not payload.get("ok") or not payload.get("dry_run"):
        raise AssertionError("Cloud adapter dry-run did not report ok/dry_run")
    request = payload.get("request", {})
    if request.get("api_key_env") != "CODEX_BLENDER_CLOUD_IMAGE_TO_3D_API_KEY":
        raise AssertionError("Cloud adapter dry-run must use an env var for API keys")


def check_image_to_3d_import_workflow() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(project_path("scripts/run_image_to_3d_import_workflow.py")),
            str(project_path("examples/image-to-3d/mock_import_workflow_job.json")),
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Image-to-3D import workflow dry-run failed: {completed.stderr}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Image-to-3D import workflow dry-run did not return JSON: {exc}") from exc
    if not payload.get("ok") or not payload.get("dry_run"):
        raise AssertionError("Image-to-3D import workflow dry-run did not report ok/dry_run")
    actions = [step.get("action") for step in payload.get("plan", [])]
    for action in ("import_asset", "fit_object_to_bounds", "setup_reference_camera", "render_scene"):
        if action not in actions:
            raise AssertionError(f"Image-to-3D import workflow missing planned action: {action}")


def check_procedural_texture_generator() -> None:
    output = project_path("assets/textures/generated/validation_noise.png")
    if output.exists():
        output.unlink()
    completed = subprocess.run(
        [
            sys.executable,
            str(project_path("scripts/generate_procedural_texture.py")),
            "noise",
            str(output),
            "--width",
            "16",
            "--height",
            "16",
            "--seed",
            "151",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Procedural texture generator failed: {completed.stderr}")
    if not output.exists():
        raise AssertionError("Procedural texture generator did not create output")
    if output.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Procedural texture generator output is not a PNG")
    output.unlink()


def check_user_texture_registration() -> None:
    config_path = project_path("examples/textures/register_user_texture.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    required = {"source", "name", "asset_id", "destination", "tags", "license", "source_note"}
    missing = sorted(required - set(config))
    if missing:
        raise AssertionError("User texture registration example missing: " + ", ".join(missing))
    if not project_path(config["source"]).exists():
        raise AssertionError(f"User texture registration source does not exist: {config['source']}")
    completed = subprocess.run(
        [
            sys.executable,
            str(project_path("scripts/register_user_texture.py")),
            config["source"],
            "--name",
            config["name"],
            "--asset-id",
            config["asset_id"],
            "--destination",
            config["destination"],
            "--tags",
            ",".join(config["tags"]),
            "--license",
            config["license"],
            "--source-note",
            config["source_note"],
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"User texture registration dry-run failed: {completed.stderr}")
    payload = json.loads(completed.stdout)
    if not payload.get("ok") or not payload.get("dry_run"):
        raise AssertionError("User texture registration dry-run did not report ok/dry_run")
    if payload.get("asset", {}).get("type") != "texture":
        raise AssertionError("User texture registration dry-run did not build a texture asset")


def check_mcp_tool_coverage() -> None:
    mcp_source = project_path("scripts/codex_blender_mcp.py").read_text(encoding="utf-8")
    declared_tools = set(re.findall(r'"name": "(blender_[^"]+)"', mcp_source))
    handled_tools = set()
    for match in re.findall(r'(?:if|elif) name == "(blender_[^"]+)"', mcp_source):
        handled_tools.add(match)

    missing_handlers = sorted(declared_tools - handled_tools)
    if missing_handlers:
        raise AssertionError("MCP tools missing handlers: " + ", ".join(missing_handlers))

    if "blender_command" not in declared_tools:
        raise AssertionError("MCP raw command tool is missing")

    action_to_tool = {"ping": "blender_health"}
    raw_only_actions = {"run_python"}
    for action in sorted(get_supported_actions()):
        if action in raw_only_actions:
            if action not in project_path("docs/mcp-tools.md").read_text(encoding="utf-8"):
                raise AssertionError(f"Raw-only MCP action is not documented: {action}")
            continue
        tool_name = action_to_tool.get(action, f"blender_{action}")
        if tool_name not in declared_tools:
            raise AssertionError(f"MCP tool missing for action {action}: expected {tool_name}")


def check_repository_hygiene() -> None:
    gitignore = project_path(".gitignore").read_text(encoding="utf-8").splitlines()
    required_ignored_paths = {
        "dist/",
        "renders/",
        "renders/compare/",
        "scenes/",
        "exports/",
        "examples/dev/*",
        "assets/references/dev/*",
        "assets/models/generated/",
        "assets/textures/generated/",
    }
    missing_ignored_paths = sorted(required_ignored_paths - set(gitignore))
    if missing_ignored_paths:
        raise AssertionError("Generated paths missing from .gitignore: " + ", ".join(missing_ignored_paths))

    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    generated_prefixes = ("dist/", "renders/", "scenes/", "exports/")
    generated_files = sorted(path for path in tracked if path.startswith(generated_prefixes))
    if generated_files:
        raise AssertionError("Generated files should not be tracked: " + ", ".join(generated_files))

    transient_files = sorted(path for path in tracked if "__pycache__/" in path or path.endswith(".pyc"))
    if transient_files:
        raise AssertionError("Transient Python cache files should not be tracked: " + ", ".join(transient_files))

    large_files = []
    max_size = 5 * 1024 * 1024
    for path in tracked:
        file_path = project_path(path)
        if file_path.exists() and file_path.is_file() and file_path.stat().st_size > max_size:
            large_files.append(path)
    if large_files:
        raise AssertionError("Tracked files exceed 5 MB: " + ", ".join(sorted(large_files)))


def check_package_zip() -> None:
    from package_addon import package_addon, read_version

    version = read_version()
    output_path = package_addon(version)
    if not output_path.exists():
        raise AssertionError("Package ZIP was not created")
    expected_name = f"codex_blender_addon_v{version}.zip"
    if output_path.name != expected_name:
        raise AssertionError(f"Unexpected package filename: {output_path.name}")
    with zipfile.ZipFile(output_path) as archive:
        names = archive.namelist()
    if names != ["codex_blender_addon.py"]:
        raise AssertionError(f"Unexpected package contents: {names}")


def run_check(name: str, func) -> None:
    func()
    print(f"OK: {name}")


def main() -> int:
    checks = [
        ("required files", check_required_files),
        ("Python syntax", check_python_syntax),
        ("JSON files", check_json_files),
        ("version alignment", check_versions),
        ("version references", check_version_references),
        ("example actions", check_examples),
        ("skill actions", check_skill_actions),
        ("README paths", check_readme_paths),
        ("bridge path normalization", check_bridge_path_normalization),
        ("BlenderMCP adapter examples", check_blendermcp_adapter_examples),
        ("asset library manifest", check_asset_library_manifest),
        ("material recipes", check_material_recipes),
        ("image-to-3D job examples", check_image_to_3d_job_examples),
        ("image-to-3D provider stub", check_image_to_3d_provider_stub),
        ("cloud image-to-3D adapter", check_cloud_image_to_3d_adapter),
        ("image-to-3D import workflow", check_image_to_3d_import_workflow),
        ("procedural texture generator", check_procedural_texture_generator),
        ("user texture registration", check_user_texture_registration),
        ("MCP tool coverage", check_mcp_tool_coverage),
        ("repository hygiene", check_repository_hygiene),
        ("package ZIP", check_package_zip),
    ]

    try:
        for name, func in checks:
            run_check(name, func)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
