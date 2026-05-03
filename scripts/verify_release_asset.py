#!/usr/bin/env python3
"""Verify the packaged Blender add-on ZIP before publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from package_addon import package_addon, read_version


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(zip_path: Path | None = None, build: bool = False) -> dict[str, object]:
    version = read_version()
    expected_name = f"codex_blender_addon_v{version}.zip"
    if build:
        zip_path = package_addon(version)
    else:
        zip_path = zip_path or ROOT / "dist" / expected_name
    if not zip_path.exists():
        raise FileNotFoundError(f"Release ZIP not found: {zip_path}")
    if zip_path.name != expected_name:
        raise ValueError(f"Expected release ZIP name {expected_name}, got {zip_path.name}")
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        addon_source = archive.read("codex_blender_addon.py").decode("utf-8") if "codex_blender_addon.py" in names else ""
    if names != ["codex_blender_addon.py"]:
        raise ValueError(f"Unexpected ZIP contents: {names}")
    expected_tuple = tuple(int(part) for part in version.split("."))
    if f'"version": {expected_tuple}' not in addon_source:
        raise ValueError(f"ZIP add-on version does not match {version}")
    size = zip_path.stat().st_size
    if size <= 0:
        raise ValueError("Release ZIP is empty")
    return {
        "ok": True,
        "version": version,
        "path": str(zip_path),
        "filename": zip_path.name,
        "size_bytes": size,
        "sha256": sha256(zip_path),
        "contents": names,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Codex Blender release ZIP.")
    parser.add_argument("--zip", dest="zip_path", help="Optional ZIP path. Defaults to dist/codex_blender_addon_v<VERSION>.zip.")
    parser.add_argument("--build", action="store_true", help="Build the package before verifying.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zip_path = Path(args.zip_path) if args.zip_path else None
    if zip_path and not zip_path.is_absolute():
        zip_path = ROOT / zip_path
    print(json.dumps(verify(zip_path, build=args.build), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
