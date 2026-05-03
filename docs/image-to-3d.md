# Image-To-3D Integration Plan

Codex Blender should treat image-to-3D as an optional provider workflow, not as a built-in promise that every image becomes a perfect model.

The default project behavior must stay offline and safe. No model weights, cloud calls, API keys, or paid services should be required for normal bridge usage.

## Goals

- Accept a user image plus optional prompt and quality settings.
- Run a configured local or cloud provider outside the Blender add-on.
- Produce a model file such as `.glb`, `.gltf`, `.obj`, or `.fbx`.
- Import the generated model into Blender, fit bounds, set camera, and render a preview.
- Record provider metadata so users know how the asset was made.

## Non-Goals

- Bundling large AI model weights.
- Hiding paid API usage.
- Pretending generated geometry is production-ready without cleanup.
- Sending images to a cloud provider unless the user explicitly configures that provider.

## Provider Contract

Every provider should expose the same small interface:

```json
{
  "provider": "local_example",
  "input_image": "assets/references/object.png",
  "prompt": "clean low-poly model of the object",
  "output": "assets/models/generated/object.glb",
  "quality": "preview",
  "metadata_output": "assets/models/generated/object.metadata.json"
}
```

The formal JSON schema lives at:

```text
schemas/image-to-3d-job.schema.json
```

An example job lives at:

```text
examples/image-to-3d/local_provider_job.json
```

Expected provider result:

```json
{
  "ok": true,
  "output": "assets/models/generated/object.glb",
  "format": "glb",
  "provider": "local_example",
  "metadata": {
    "source_image": "assets/references/object.png",
    "prompt": "clean low-poly model of the object",
    "license": "user-generated",
    "notes": "Requires cleanup before production use."
  }
}
```

## Local Provider

A local provider runs on the user's machine. It may require:

- A separate executable or Python environment.
- GPU drivers and enough VRAM.
- Downloaded model weights stored outside this repository.
- Longer runtime and more disk space.

The plugin should only call a configured command path. If the command is missing, it should return a clear setup error and should not install heavy dependencies automatically.

Use the local runner for provider integration tests:

```powershell
python scripts\run_image_to_3d_job.py examples\image-to-3d\local_provider_job.json
```

The runner resolves the executable in this order:

1. `--provider-command`
2. `provider_command` in the job JSON
3. `CODEX_BLENDER_IMAGE_TO_3D_COMMAND`

The configured command is called with:

```text
--job JOB.json --input-image IMAGE.png --output MODEL.glb --quality preview --provider local_stub
```

Missing commands or placeholder commands return `MissingImageTo3DProviderCommand` with setup instructions. This is intentional: the repository does not bundle model weights or install heavy AI dependencies.

## Cloud Provider

A cloud provider runs through a vendor API. It may require:

- API key stored in an environment variable.
- Explicit user confirmation before upload.
- Cost and rate-limit awareness.
- Provider terms and output license review.

The plugin must not commit secrets or write API keys into examples. Example configs should use placeholder environment variable names.

The built-in cloud adapter is only a documented pattern:

```powershell
python scripts\run_image_to_3d_job.py examples\image-to-3d\cloud_placeholder_job.json --dry-run
```

This dry-run works without an API key and prints the request metadata that would be sent. A real run requires the environment variable named by `api_key_env`, defaults to `CODEX_BLENDER_CLOUD_IMAGE_TO_3D_API_KEY`, and currently returns `CloudProviderNotImplemented` because no vendor API is bundled.

Cloud adapter jobs use:

```json
{
  "provider": "cloud_placeholder",
  "provider_adapter": "cloud_placeholder",
  "api_key_env": "CODEX_BLENDER_CLOUD_IMAGE_TO_3D_API_KEY",
  "endpoint": "https://example.invalid/image-to-3d"
}
```

Replace the placeholder adapter with vendor-specific code only after confirming upload behavior, cost, rate limits, and output-license terms.

## Inputs

Required:

- `input_image`: project-relative or absolute image path.
- `provider`: configured provider name.
- `output`: desired generated model path.

Optional:

- `prompt`
- `quality`: `draft`, `preview`, or `final`
- `seed`
- `timeout_seconds`
- `provider_command`: local command string or string list
- `provider_adapter`: built-in adapter name, such as `cloud_placeholder`
- `api_key_env`: cloud API key environment variable name
- `endpoint`: cloud adapter endpoint
- `import_options`: location, rotation, scale, fit bounds, target size

## Outputs

The provider should produce:

- Model file under `assets/models/generated/` or another user-chosen path.
- Metadata JSON next to the model.
- Optional preview render under an ignored generated folder or a stable asset preview path if the user wants to keep it.

## Blender Import Loop

After generation:

1. Validate that the output model exists.
2. Import with `import_asset`.
3. Fit with `fit_object_to_bounds`.
4. Apply basic material or preserve provider materials.
5. Set camera and render a preview.
6. Add a manifest entry only when the user wants to keep the generated asset.

## Limitations

Image-to-3D output can have bad topology, missing backsides, warped proportions, baked artifacts, poor UVs, or unusable materials. It usually needs manual cleanup, retopology, remeshing, material work, and scale adjustment before production use.

For reference matching, continue using the render-compare-adjust loop. The image-to-3D provider is only a starting point.
