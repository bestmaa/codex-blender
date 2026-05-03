#!/usr/bin/env python3
"""Provider adapter interfaces for optional image-to-3D integrations."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CLOUD_API_KEY_ENV = "CODEX_BLENDER_CLOUD_IMAGE_TO_3D_API_KEY"


@dataclass(frozen=True)
class ImageTo3DJob:
    provider: str
    input_image: Path
    output: Path
    quality: str
    prompt: str = ""
    seed: int | None = None
    metadata_output: Path | None = None
    api_key_env: str = DEFAULT_CLOUD_API_KEY_ENV
    endpoint: str = "https://example.invalid/image-to-3d"

    @classmethod
    def from_mapping(cls, job: dict[str, Any], root: Path) -> "ImageTo3DJob":
        def resolve(value: str) -> Path:
            path = Path(value)
            return path if path.is_absolute() else root / path

        metadata_output = job.get("metadata_output")
        return cls(
            provider=str(job["provider"]),
            input_image=resolve(str(job["input_image"])),
            output=resolve(str(job["output"])),
            quality=str(job["quality"]),
            prompt=str(job.get("prompt", "")),
            seed=job.get("seed"),
            metadata_output=resolve(str(metadata_output)) if metadata_output else None,
            api_key_env=str(job.get("api_key_env", DEFAULT_CLOUD_API_KEY_ENV)),
            endpoint=str(job.get("endpoint", "https://example.invalid/image-to-3d")),
        )


class ImageTo3DProviderAdapter:
    name = "base"

    def run(self, job: ImageTo3DJob, *, dry_run: bool = False) -> dict[str, Any]:
        raise NotImplementedError


class CloudPlaceholderAdapter(ImageTo3DProviderAdapter):
    """Documented cloud adapter skeleton that never uploads by itself."""

    name = "cloud_placeholder"

    def run(self, job: ImageTo3DJob, *, dry_run: bool = False) -> dict[str, Any]:
        request_preview = {
            "endpoint": job.endpoint,
            "provider": job.provider,
            "input_image": str(job.input_image),
            "output": str(job.output),
            "quality": job.quality,
            "prompt": job.prompt,
            "seed": job.seed,
            "api_key_env": job.api_key_env,
        }
        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "adapter": self.name,
                "message": "Cloud adapter dry-run prepared request metadata without reading an API key or uploading.",
                "request": request_preview,
            }

        api_key = os.environ.get(job.api_key_env)
        if not api_key:
            return {
                "ok": False,
                "errorType": "MissingCloudProviderApiKey",
                "adapter": self.name,
                "message": f"Set {job.api_key_env} before running this cloud image-to-3D adapter.",
                "setup": [
                    "Create an account with the cloud image-to-3D provider you choose.",
                    f"Store the API key in the {job.api_key_env} environment variable.",
                    "Review provider cost, upload, and output-license terms before running.",
                    "Use --dry-run first to inspect the request without uploading.",
                ],
                "request": request_preview,
            }

        return {
            "ok": False,
            "errorType": "CloudProviderNotImplemented",
            "adapter": self.name,
            "message": "This placeholder documents the adapter shape but does not call a vendor API.",
            "request": request_preview,
        }


ADAPTERS: dict[str, ImageTo3DProviderAdapter] = {
    CloudPlaceholderAdapter.name: CloudPlaceholderAdapter(),
}


def run_adapter(adapter_name: str, job: ImageTo3DJob, *, dry_run: bool = False) -> dict[str, Any]:
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        return {
            "ok": False,
            "errorType": "UnknownImageTo3DAdapter",
            "message": f"Unknown image-to-3D adapter: {adapter_name}",
            "available_adapters": sorted(ADAPTERS),
        }
    result = adapter.run(job, dry_run=dry_run)
    if result.get("ok") and job.metadata_output and not dry_run:
        job.metadata_output.parent.mkdir(parents=True, exist_ok=True)
        job.metadata_output.write_text(
            json.dumps(
                {
                    "provider": job.provider,
                    "adapter": adapter_name,
                    "output": str(job.output),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return result
