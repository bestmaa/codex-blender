#!/usr/bin/env python3
"""Validate the Codex Blender project without launching Blender."""

from __future__ import annotations

import json
import py_compile
import re
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
    "skills/blender/SKILL.md",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/add_reference_image.json",
    "examples/apply_table_texture.json",
    "examples/apply_scaled_wood_texture.json",
    "examples/apply_material_preset.json",
    "examples/import_asset.json",
    "examples/create_scene_from_reference.json",
    "examples/render_scene.json",
    "examples/save_blend.json",
    "examples/inspect_rig.json",
    "assets/models/sample_pyramid.obj",
    "docs/quickstart-demo.md",
]

PYTHON_FILES = [
    "blender_addon/codex_blender_addon.py",
    "bridge/codex_blender_bridge.py",
    "scripts/codex_blender_mcp.py",
    "scripts/package_addon.py",
    "scripts/validate_project.py",
]

JSON_FILES = [
    ".codex-plugin/plugin.json",
    ".mcp.json",
    ".agents/plugins/marketplace.json",
    "examples/create_room.json",
    "examples/create_outdoor_scene.json",
    "examples/create_table_model.json",
    "examples/add_reference_image.json",
    "examples/apply_table_texture.json",
    "examples/apply_scaled_wood_texture.json",
    "examples/apply_material_preset.json",
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
    for relative_path in JSON_FILES:
        json.loads(project_path(relative_path).read_text(encoding="utf-8"))


def check_versions() -> None:
    manifest = json.loads(project_path(".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    addon_source = project_path("blender_addon/codex_blender_addon.py").read_text(encoding="utf-8")
    expected = tuple(int(part) for part in version.split("."))
    if f'"version": {expected}' not in addon_source:
        raise AssertionError(f"Add-on bl_info version does not match plugin version {version}")


def check_examples() -> None:
    expected_actions = {
        "examples/create_room.json": "create_room",
        "examples/create_outdoor_scene.json": "create_outdoor_scene",
        "examples/create_table_model.json": "create_table_model",
        "examples/add_reference_image.json": "add_reference_image",
        "examples/apply_table_texture.json": "apply_texture_material",
        "examples/apply_scaled_wood_texture.json": "apply_texture_material",
        "examples/apply_material_preset.json": "apply_material_preset",
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


def check_readme_paths() -> None:
    readme = project_path("README.md").read_text(encoding="utf-8")
    referenced_paths = sorted(set(re.findall(r"(?:examples|docs|assets/models|scripts|bridge|blender_addon)/[\\w./-]+", readme)))
    missing = [path for path in referenced_paths if not project_path(path).exists()]
    if missing:
        raise AssertionError("README references missing paths: " + ", ".join(missing))


def check_package_zip() -> None:
    from package_addon import package_addon, read_version

    version = read_version()
    output_path = package_addon(version)
    if not output_path.exists():
        raise AssertionError("Package ZIP was not created")
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
        ("example actions", check_examples),
        ("README paths", check_readme_paths),
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
