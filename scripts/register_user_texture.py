#!/usr/bin/env python3
"""Copy a user texture into the project and optionally register it in assets/library.json."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned or "user_texture"


def load_library() -> dict[str, Any]:
    path = ROOT / "assets" / "library.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_library(library: dict[str, Any]) -> None:
    path = ROOT / "assets" / "library.json"
    path.write_text(json.dumps(library, indent=2), encoding="utf-8")


def build_asset(asset_id: str, name: str, destination: Path, tags: list[str], license_text: str, source_note: str) -> dict[str, Any]:
    relative_path = destination.relative_to(ROOT).as_posix()
    return {
        "id": asset_id,
        "name": name,
        "type": "texture",
        "tags": tags,
        "path": relative_path,
        "scale_hints": {
            "unit": "texture_repeat",
            "default_scale": 1.0,
            "target_size": [2.0, 2.0, 0.0],
        },
        "license": license_text,
        "source": source_note,
        "preview_path": relative_path,
    }


def register_asset(asset: dict[str, Any], replace: bool) -> None:
    library = load_library()
    assets = library.setdefault("assets", [])
    existing_index = next((index for index, item in enumerate(assets) if item.get("id") == asset["id"]), None)
    if existing_index is not None:
        if not replace:
            raise SystemExit(f"Asset id already exists: {asset['id']}. Use --replace to update it.")
        assets[existing_index] = asset
    else:
        assets.append(asset)
    save_library(library)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy and optionally register a user texture image.")
    parser.add_argument("source", help="Source image path.")
    parser.add_argument("--name", help="Human-readable asset name.")
    parser.add_argument("--asset-id", help="Asset library id. Defaults to a slug of the name/source filename.")
    parser.add_argument("--destination", help="Project-relative destination path.")
    parser.add_argument("--tags", default="user,texture", help="Comma-separated tags.")
    parser.add_argument("--license", default="User-provided asset", help="License note.")
    parser.add_argument("--source-note", default="User-provided local image", help="Source note.")
    parser.add_argument("--register", action="store_true", help="Add or update assets/library.json.")
    parser.add_argument("--replace", action="store_true", help="Replace existing asset id when registering.")
    parser.add_argument("--dry-run", action="store_true", help="Print the copy/register plan without writing files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = project_path(args.source)
    if not source.exists():
        raise SystemExit(f"Source texture not found: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"Unsupported texture extension: {source.suffix}")

    name = args.name or source.stem.replace("_", " ").replace("-", " ").title()
    asset_id = args.asset_id or slug(name)
    destination = project_path(args.destination or f"assets/textures/{asset_id}{source.suffix.lower()}")
    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    asset = build_asset(asset_id, name, destination, tags, args.license, args.source_note)
    payload = {
        "ok": True,
        "dry_run": args.dry_run,
        "source": str(source),
        "destination": str(destination),
        "registered": bool(args.register),
        "asset": asset,
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if args.register:
        register_asset(asset, replace=args.replace)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
