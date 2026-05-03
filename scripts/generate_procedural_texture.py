#!/usr/bin/env python3
"""Generate simple local bitmap textures without external dependencies."""

from __future__ import annotations

import argparse
import json
import math
import random
import struct
import zlib
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


PALETTES = {
    "wood": ((139, 92, 45), (205, 152, 88)),
    "fabric": ((55, 72, 96), (112, 132, 158)),
    "stone": ((96, 99, 101), (178, 178, 172)),
    "noise": ((48, 52, 58), (210, 214, 218)),
    "stripes": ((230, 232, 224), (70, 104, 138)),
}


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def clamp(value: float) -> int:
    return max(0, min(255, int(round(value))))


def mix(color_a: tuple[int, int, int], color_b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(clamp(a + (b - a) * amount) for a, b in zip(color_a, color_b))


def jitter(color: tuple[int, int, int], rng: random.Random, amount: int) -> tuple[int, int, int]:
    return tuple(clamp(channel + rng.randint(-amount, amount)) for channel in color)


def write_png(path: Path, width: int, height: int, pixels: Iterable[tuple[int, int, int]]) -> None:
    rows = []
    iterator = iter(pixels)
    for _ in range(height):
        row = bytearray([0])
        for _ in range(width):
            row.extend(next(iterator))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, level=9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def generate_pixels(kind: str, width: int, height: int, seed: int) -> list[tuple[int, int, int]]:
    rng = random.Random(seed)
    base, accent = PALETTES[kind]
    pixels: list[tuple[int, int, int]] = []
    stone_cells = {
        (x, y): rng.random()
        for x in range((width // 32) + 3)
        for y in range((height // 32) + 3)
    }
    for y in range(height):
        for x in range(width):
            nx = x / max(width - 1, 1)
            ny = y / max(height - 1, 1)
            if kind == "wood":
                grain = math.sin((nx * 24.0 + math.sin(ny * 18.0) * 0.8) * math.pi)
                rings = math.sin((nx * 7.0 + ny * 3.0) * math.pi)
                amount = 0.45 + 0.25 * grain + 0.12 * rings + rng.uniform(-0.05, 0.05)
                color = jitter(mix(base, accent, amount), rng, 7)
            elif kind == "fabric":
                weave = ((x % 10) / 10.0) * 0.18 + ((y % 8) / 8.0) * 0.18
                cross = 0.18 if x % 6 == 0 or y % 6 == 0 else 0.0
                amount = 0.35 + weave + cross + rng.uniform(-0.04, 0.04)
                color = jitter(mix(base, accent, amount), rng, 5)
            elif kind == "stone":
                cell = stone_cells[(x // 32, y // 32)]
                vein = 0.22 if (x + y + int(cell * 40)) % 37 in {0, 1} else 0.0
                amount = 0.25 + cell * 0.45 + vein + rng.uniform(-0.06, 0.06)
                color = jitter(mix(base, accent, amount), rng, 9)
            elif kind == "stripes":
                stripe = ((x // max(width // 12, 1)) % 2)
                edge = 0.08 * math.sin(ny * math.pi * 12.0)
                color = jitter(mix(base, accent, 0.18 + stripe * 0.72 + edge), rng, 4)
            else:
                amount = rng.random()
                color = mix(base, accent, amount)
            pixels.append(color)
    return pixels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a PNG basecolor texture.")
    parser.add_argument("kind", choices=sorted(PALETTES), help="Texture family to generate.")
    parser.add_argument("output", help="Output PNG path.")
    parser.add_argument("--width", type=int, default=512, help="Texture width in pixels.")
    parser.add_argument("--height", type=int, default=512, help="Texture height in pixels.")
    parser.add_argument("--seed", type=int, default=1, help="Deterministic random seed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("width and height must be positive")
    output = project_path(args.output)
    pixels = generate_pixels(args.kind, args.width, args.height, args.seed)
    write_png(output, args.width, args.height, pixels)
    print(
        json.dumps(
            {
                "ok": True,
                "kind": args.kind,
                "output": str(output),
                "width": args.width,
                "height": args.height,
                "seed": args.seed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
