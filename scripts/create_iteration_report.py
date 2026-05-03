#!/usr/bin/env python3
"""Create a render/reference iteration report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def normalize_paths(values: list[str]) -> list[str]:
    return [str(project_path(value)) for value in values]


def write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = [
        f"# {report['title']}",
        "",
        f"- Created: `{report['created_at']}`",
        f"- Reference: `{report['reference']}`",
        "",
        "## Commands",
        "",
    ]
    commands = report.get("commands", [])
    lines.extend(f"- `{command}`" for command in commands)
    lines.extend(["", "## Renders", ""])
    lines.extend(f"- `{render}`" for render in report.get("renders", []))
    lines.extend(["", "## Contact Sheets", ""])
    lines.extend(f"- `{sheet}`" for sheet in report.get("contact_sheets", []))
    lines.extend(["", "## Metrics", ""])
    lines.extend(f"- `{metric}`" for metric in report.get("metrics", []))
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in report.get("notes", []))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_report(args: argparse.Namespace) -> dict[str, object]:
    output = project_path(args.output)
    markdown_output = project_path(args.markdown_output) if args.markdown_output else None
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "ok": True,
        "title": args.title,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reference": str(project_path(args.reference)),
        "commands": args.command,
        "renders": normalize_paths(args.render),
        "contact_sheets": normalize_paths(args.contact_sheet),
        "metrics": normalize_paths(args.metrics),
        "notes": args.note,
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["output"] = str(output)
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(markdown_output, report)
        report["markdown_output"] = str(markdown_output)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a JSON/Markdown report for a render comparison iteration.")
    parser.add_argument("reference", help="Reference image path.")
    parser.add_argument("output", help="Output JSON report path.")
    parser.add_argument("--title", default="Render Iteration Report", help="Report title.")
    parser.add_argument("--markdown-output", help="Optional Markdown report path.")
    parser.add_argument("--command", action="append", default=[], help="Command run during the iteration. Repeatable.")
    parser.add_argument("--render", action="append", default=[], help="Render output path. Repeatable.")
    parser.add_argument("--contact-sheet", action="append", default=[], help="Contact sheet path. Repeatable.")
    parser.add_argument("--metrics", action="append", default=[], help="Metrics JSON path. Repeatable.")
    parser.add_argument("--note", action="append", default=[], help="Human note. Repeatable.")
    return parser.parse_args()


def main() -> int:
    print(json.dumps(create_report(parse_args()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
