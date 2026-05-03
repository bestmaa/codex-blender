# GitHub Release Workflow

Use this checklist before publishing a GitHub release. Do not publish, tag, or upload a release asset unless the user explicitly confirms.

## Preflight

1. Confirm the repository remote:

```powershell
git remote -v
```

2. Confirm branch and working tree:

```powershell
git status --short
git branch --show-current
```

3. Run validation:

```powershell
python scripts\validate_project.py
```

4. Confirm the version in:

- `.codex-plugin/plugin.json`
- `blender_addon/codex_blender_addon.py`
- `scripts/codex_blender_mcp.py`
- `README.md`

## Package ZIP

Build the add-on ZIP:

```powershell
python scripts\package_addon.py
```

Expected output:

```text
dist/codex_blender_addon_vX.Y.Z.zip
```

The ZIP should contain only:

```text
codex_blender_addon.py
```

## Branch And Push

Only push after user approval:

```powershell
git push origin <branch>
```

If creating a release branch, use the `codex/` prefix unless the user asks for a different name.

## Tag

Only create and push a tag after user approval:

```powershell
git tag vX.Y.Z
git push origin vX.Y.Z
```

## Release Notes

Prepare release notes from:

- `docs/release-notes-v1.md`
- Recent commits since the previous tag.
- Validation result.
- Known limitations from `docs/known-limitations.md`.

Release notes should include:

- Version.
- What changed.
- Install steps.
- Validation summary.
- Known limitations.
- ZIP asset name.

## Publish

Only publish after explicit confirmation:

```powershell
gh release create vX.Y.Z dist\codex_blender_addon_vX.Y.Z.zip --title "Codex Blender vX.Y.Z" --notes-file RELEASE_NOTES.md
```

Do not use draft/publish commands automatically. If the user wants a draft release, confirm title, tag, notes, and ZIP path before creating it.
