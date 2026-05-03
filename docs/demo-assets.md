# Demo Assets

The repository keeps a small stable asset set for validation and release smoke tests.

## Model

```text
assets/models/sample_pyramid.obj
```

Purpose:

- Verifies `.obj` import.
- Verifies asset fitting and placement helpers.
- Keeps model tests lightweight.

## Reference Image

```text
assets/references/modern_table_reference.png
```

Purpose:

- Verifies reference image planes.
- Verifies reference camera and side-by-side comparison workflows.
- Provides a stable visual target for table modeling examples.

## Texture

```text
assets/textures/oak_wood_basecolor.png
```

Purpose:

- Verifies image texture material application.
- Supports scaled and multi-map texture command examples.

## Local Experiments

One-off reference images belong in:

```text
assets/references/dev/
```

That folder is ignored by Git except for its README. Keep stable release assets directly under `assets/models/`, `assets/references/`, or `assets/textures/`.
