#!/usr/bin/env python3
"""Generate GitHub release draft metadata without publishing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_release_asset import verify


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_notes(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def create_draft(args: argparse.Namespace) -> dict[str, object]:
    asset = verify(build=args.build)
    version = str(asset["version"])
    title = args.title or f"Codex Blender v{version}"
    tag = args.tag or f"v{version}"
    notes_source = project_path(args.notes)
    base_notes = read_notes(notes_source)
    body = "\n\n".join(
        part
        for part in [
            base_notes,
            "## Release Asset",
            f"- ZIP: `{asset['filename']}`",
            f"- Size: `{asset['size_bytes']}` bytes",
            f"- SHA256: `{asset['sha256']}`",
            "",
            "Publishing must remain manual and user-confirmed.",
        ]
        if part
    )
    output_json = project_path(args.output_json)
    output_body = project_path(args.output_body)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_body.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "title": title,
        "tag": tag,
        "body_path": str(output_body),
        "zip_path": asset["path"],
        "zip_sha256": asset["sha256"],
        "publish": False,
    }
    output_body.write_text(body + "\n", encoding="utf-8")
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["output_json"] = str(output_json)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate release title/body/checksum metadata without publishing.")
    parser.add_argument("--notes", default="docs/release-notes-v1.md", help="Release notes source Markdown.")
    parser.add_argument("--title", help="Release title override.")
    parser.add_argument("--tag", help="Release tag override.")
    parser.add_argument("--output-json", default="dist/release-draft.json", help="Output JSON metadata path.")
    parser.add_argument("--output-body", default="dist/release-draft.md", help="Output Markdown body path.")
    parser.add_argument("--build", action="store_true", help="Build and verify the ZIP before drafting metadata.")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(create_draft(parse_args()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
