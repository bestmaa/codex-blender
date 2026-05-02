#!/usr/bin/env python3
"""Package the Blender add-on as an installable ZIP."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
ADDON_PATH = ROOT / "blender_addon" / "codex_blender_addon.py"
DIST_DIR = ROOT / "dist"


def read_version() -> str:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest["version"]


def package_addon(version: str | None = None) -> Path:
    version = version or read_version()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DIST_DIR / f"codex_blender_addon_v{version}.zip"

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(ADDON_PATH, arcname=ADDON_PATH.name)

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Blender add-on ZIP.")
    parser.add_argument("--version", help="Override version used in the ZIP filename.")
    args = parser.parse_args()

    output_path = package_addon(args.version)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
