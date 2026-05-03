#!/usr/bin/env python3
"""Compute basic non-semantic image difference metrics for PNG files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from create_contact_sheet import read_png


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def crop_image(width: int, height: int, pixels: list[tuple[int, int, int]], crop: tuple[int, int, int, int] | None) -> tuple[int, int, list[tuple[int, int, int]]]:
    if crop is None:
        return width, height, pixels
    x, y, crop_width, crop_height = crop
    if x < 0 or y < 0 or crop_width <= 0 or crop_height <= 0:
        raise ValueError("crop must be x,y,width,height with non-negative origin and positive size")
    x2 = min(width, x + crop_width)
    y2 = min(height, y + crop_height)
    cropped = []
    for row in range(y, y2):
        for col in range(x, x2):
            cropped.append(pixels[row * width + col])
    return x2 - x, y2 - y, cropped


def average_color(pixels: list[tuple[int, int, int]]) -> list[float]:
    count = max(len(pixels), 1)
    return [round(sum(pixel[channel] for pixel in pixels) / count, 3) for channel in range(3)]


def histogram(pixels: list[tuple[int, int, int]], bins: int) -> list[float]:
    counts = [0] * (bins * 3)
    for pixel in pixels:
        for channel, value in enumerate(pixel):
            index = min(bins - 1, int(value * bins / 256))
            counts[channel * bins + index] += 1
    total = max(len(pixels), 1)
    return [count / total for count in counts]


def l1_distance(values_a: list[float], values_b: list[float]) -> float:
    return round(sum(abs(a - b) for a, b in zip(values_a, values_b)), 6)


def parse_crop(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--crop must be x,y,width,height")
    return parts[0], parts[1], parts[2], parts[3]


def compare(args: argparse.Namespace) -> dict[str, object]:
    reference_path = project_path(args.reference)
    render_path = project_path(args.render)
    crop = parse_crop(args.crop)
    ref_width, ref_height, ref_pixels = crop_image(*read_png(reference_path), crop)
    render_width, render_height, render_pixels = crop_image(*read_png(render_path), crop)
    ref_hist = histogram(ref_pixels, args.bins)
    render_hist = histogram(render_pixels, args.bins)
    ref_avg = average_color(ref_pixels)
    render_avg = average_color(render_pixels)
    result = {
        "ok": True,
        "reference": str(reference_path),
        "render": str(render_path),
        "crop": list(crop) if crop else None,
        "reference_dimensions": [ref_width, ref_height],
        "render_dimensions": [render_width, render_height],
        "dimension_delta": [render_width - ref_width, render_height - ref_height],
        "reference_average_rgb": ref_avg,
        "render_average_rgb": render_avg,
        "average_rgb_delta": [round(render_avg[index] - ref_avg[index], 3) for index in range(3)],
        "histogram_bins_per_channel": args.bins,
        "histogram_l1_distance": l1_distance(ref_hist, render_hist),
        "note": "These are rough pixel/color metrics, not semantic visual accuracy.",
    }
    if args.output:
        output = project_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["output"] = str(output)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two PNG files with basic non-semantic metrics.")
    parser.add_argument("reference", help="Reference PNG path.")
    parser.add_argument("render", help="Render PNG path.")
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    parser.add_argument("--bins", type=int, default=16, help="Histogram bins per RGB channel.")
    parser.add_argument("--crop", help="Optional crop as x,y,width,height applied to both images.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.bins <= 0:
        raise SystemExit("--bins must be positive")
    print(json.dumps(compare(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
