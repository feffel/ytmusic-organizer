# Collaborator Workflows

This page is for repository collaborators/maintainers, not end users.

## Demo Asset Generation

Use demo scripts in `scripts/demo/` to record/render validation media:

```bash
make demo-record
make demo-render
make demo-check
```

Notes:
- Generated media is not committed except for the curated README asset `docs/assets/demo.gif`.
- `make demo-render` writes ignored outputs under `artifacts/demo/` and refreshes `docs/assets/demo.gif`.

## Launch Bundle Generation

Use launch helpers in `scripts/launch/`:

```bash
make launch-generate
```

This generates timestamped launch input bundles under ignored artifacts.

## Release/CI Workflows

- `.github/workflows/ci.yml`
- `.github/workflows/release-pypi.yml`
- `.github/workflows/release-testpypi.yml`
- `.github/workflows/dependency-review.yml`
