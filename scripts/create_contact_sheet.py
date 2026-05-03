#!/usr/bin/env python3
"""Create a side-by-side PNG contact sheet from reference and render images."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"Not a PNG file: {path}")
    offset = len(PNG_SIGNATURE)
    width = height = color_type = bit_depth = None
    compressed = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or color_type not in {2, 6} or compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError(f"Unsupported PNG format: {path}")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if width is None or height is None or color_type is None:
        raise ValueError(f"PNG missing IHDR: {path}")

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows: list[bytearray] = []
    cursor = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"Unsupported PNG filter {filter_type}: {path}")
        rows.append(row)
        previous = row

    pixels: list[tuple[int, int, int]] = []
    for row in rows:
        for index in range(0, len(row), channels):
            pixels.append((row[index], row[index + 1], row[index + 2]))
    return width, height, pixels


def write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    rows = []
    cursor = 0
    for _ in range(height):
        row = bytearray([0])
        for _ in range(width):
            row.extend(pixels[cursor])
            cursor += 1
        rows.append(bytes(row))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    path.parent.mkdir(parents=True, exist_ok=True)
    png = PNG_SIGNATURE
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), level=9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def resize_nearest(width: int, height: int, pixels: list[tuple[int, int, int]], target_height: int) -> tuple[int, int, list[tuple[int, int, int]]]:
    if height == target_height:
        return width, height, pixels
    target_width = max(1, round(width * target_height / height))
    resized = []
    for y in range(target_height):
        source_y = min(height - 1, int(y * height / target_height))
        for x in range(target_width):
            source_x = min(width - 1, int(x * width / target_width))
            resized.append(pixels[source_y * width + source_x])
    return target_width, target_height, resized


def paste(canvas: list[tuple[int, int, int]], canvas_width: int, x_offset: int, y_offset: int, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    for y in range(height):
        for x in range(width):
            canvas[(y + y_offset) * canvas_width + x + x_offset] = pixels[y * width + x]


def create_contact_sheet(args: argparse.Namespace) -> dict[str, object]:
    reference_path = project_path(args.reference)
    render_path = project_path(args.render)
    output_path = project_path(args.output)
    reference = read_png(reference_path)
    render = read_png(render_path)
    target_height = args.height
    ref_width, ref_height, ref_pixels = resize_nearest(*reference, target_height=target_height)
    render_width, render_height, render_pixels = resize_nearest(*render, target_height=target_height)
    gap = args.gap
    canvas_width = ref_width + render_width + gap
    canvas_height = target_height
    canvas = [(245, 245, 242)] * (canvas_width * canvas_height)
    paste(canvas, canvas_width, 0, 0, ref_width, ref_height, ref_pixels)
    paste(canvas, canvas_width, ref_width + gap, 0, render_width, render_height, render_pixels)
    write_png(output_path, canvas_width, canvas_height, canvas)
    metadata = {
        "ok": True,
        "reference": str(reference_path),
        "render": str(render_path),
        "output": str(output_path),
        "reference_label": args.reference_label,
        "render_label": args.render_label,
        "width": canvas_width,
        "height": canvas_height,
        "gap": gap,
    }
    if args.metadata_output:
        metadata_path = project_path(args.metadata_output)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        metadata["metadata_output"] = str(metadata_path)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a reference/render contact sheet PNG.")
    parser.add_argument("reference", help="Reference PNG path.")
    parser.add_argument("render", help="Render PNG path.")
    parser.add_argument("output", help="Output contact sheet PNG path.")
    parser.add_argument("--reference-label", default="Reference", help="Metadata label for the reference image.")
    parser.add_argument("--render-label", default="Render", help="Metadata label for the render image.")
    parser.add_argument("--metadata-output", help="Optional JSON metadata output path.")
    parser.add_argument("--height", type=int, default=540, help="Output image height.")
    parser.add_argument("--gap", type=int, default=16, help="Gap between images.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.height <= 0 or args.gap < 0:
        raise SystemExit("height must be positive and gap cannot be negative")
    print(json.dumps(create_contact_sheet(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
