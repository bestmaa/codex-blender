#!/usr/bin/env python3
"""Send JSON commands to the Codex Blender add-on."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URL = "http://127.0.0.1:8765/command"


def load_payload(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def send_command(payload: dict, url: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a command to Blender.")
    parser.add_argument("payload", help="Path to a JSON command file, or inline JSON.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Bridge URL. Default: {DEFAULT_URL}")
    args = parser.parse_args()

    try:
        result = send_command(load_payload(args.payload), args.url)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2
    except urllib.error.URLError as exc:
        print(f"Could not reach Blender bridge: {exc}", file=sys.stderr)
        return 3

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

