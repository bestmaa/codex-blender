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
    "scripts/codex_blender_mcp.py",
    "scripts/package_addon.py",
    "scripts/smoke_test_bridge.py",
    "skills/blender/SKILL.md",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/create_chair_model.json",
    "examples/create_sofa_model.json",
    "examples/create_plant_model.json",
    "examples/create_lamp_model.json",
    "examples/create_furniture_set.json",
    "examples/create_room_layout.json",
    "examples/list_assets.json",
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
    "examples/setup_reference_camera.json",
    "examples/setup_compare_view.json",
    "examples/export_table_glb.json",
    "examples/export_table_obj.json",
    "examples/import_asset.json",
    "examples/create_scene_from_reference.json",
    "examples/render_scene.json",
    "examples/save_blend.json",
    "examples/inspect_rig.json",
    "assets/models/sample_pyramid.obj",
    "docs/quickstart-demo.md",
    "docs/commands.md",
    "docs/mcp-tools.md",
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
    "scripts/codex_blender_mcp.py",
    "scripts/package_addon.py",
    "scripts/smoke_test_bridge.py",
    "scripts/validate_project.py",
]

JSON_FILES = [
    ".codex-plugin/plugin.json",
    ".mcp.json",
    ".agents/plugins/marketplace.json",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/create_chair_model.json",
    "examples/create_sofa_model.json",
    "examples/create_plant_model.json",
    "examples/create_lamp_model.json",
    "examples/create_furniture_set.json",
    "examples/create_room_layout.json",
    "examples/list_assets.json",
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
    "examples/setup_reference_camera.json",
    "examples/setup_compare_view.json",
    "examples/export_table_glb.json",
    "examples/export_table_obj.json",
    "examples/import_asset.json",
    "examples/create_scene_from_reference.json",
    "examples/render_scene.json",
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
        "examples/create_table_model.json": "create_table_model",
        "examples/create_chair_model.json": "create_chair_model",
        "examples/create_sofa_model.json": "create_sofa_model",
        "examples/create_plant_model.json": "create_plant_model",
        "examples/create_lamp_model.json": "create_lamp_model",
        "examples/create_furniture_set.json": "create_furniture_set",
        "examples/create_room_layout.json": "create_room_layout",
        "examples/list_assets.json": "list_assets",
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
        "examples/setup_reference_camera.json": "setup_reference_camera",
        "examples/setup_compare_view.json": "setup_compare_view",
        "examples/export_table_glb.json": "export_glb",
        "examples/export_table_obj.json": "export_obj",
        "examples/import_asset.json": "import_asset",
        "examples/create_scene_from_reference.json": "create_scene_from_reference",
        "examples/render_scene.json": "render_scene",
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
        "scenes/",
        "exports/",
        "examples/dev/*",
        "assets/references/dev/*",
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
