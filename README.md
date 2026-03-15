# ytmusic-organizer

Organize your YouTube Music likes into practical playlists with a guided first-time setup and weekly incremental sync.

## Features

- Guided onboarding: `ytmo init --bootstrap`
- First bootstrap is non-destructive (create/populate only)
- Weekly incremental sync
- Explicit destructive reset with confirmation
- Manual mode (copy/paste prompt workflow) and optional OpenAI API mode

## Install

### Recommended (PyPI)

```bash
pipx install ytmusic-organizer
```

### From GitHub (if you prefer source install)

```bash
pipx install git+https://github.com/<org-or-user>/ytmusic-organizer.git
```

## Quickstart

1. Prepare your YTMusic auth JSON.
   - Generate it using the official ytmusicapi guide: [Browser Authentication](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html).
   - Use that file with this tool:
     - default relative auth path resolves to `<workspace>/browser.json`
     - or pass absolute path using `--auth-file /absolute/path/to/browser.json`
   - Relative auth path defaults to `<workspace>/browser.json` (workspace default is `.ytmo`).
   - Recommended: pass an absolute path with `--auth-file`.
2. Run guided setup:

```bash
ytmo init --bootstrap --workspace .ytmo
```

Recommended with explicit absolute auth path:

```bash
ytmo init --auth-file /absolute/path/to/browser.json --bootstrap --workspace .ytmo
```

3. For weekly updates:

```bash
ytmo weekly-sync --workspace .ytmo
```

4. For full destructive rebuild:

```bash
ytmo full-reset --workspace .ytmo --yes
```

## Commands

- `ytmo init [--bootstrap] [--mode manual|api] [--auth-file PATH]`
- `ytmo bootstrap [--mode manual|api]`
- `ytmo weekly-sync [--mode manual|api]`
- `ytmo full-reset [--yes] [--mode manual|api]`
- `ytmo preview [--plan PATH]`

Common option:

- `--workspace` (default `.ytmo`)

## Modes

### Manual mode (default)

The CLI exports song JSON and waits for your model response JSON file:

- full flows read/write `.ytmo/data/playlist_plan.json`
- weekly sync reads/writes `.ytmo/data/new_plan.json`

Prompt templates are packaged in `ytmusic_organizer/prompts/`.

### API mode

Requires:

- `OPENAI_API_KEY`

Run with `--mode api` to auto-generate plan JSON.

## Safety and state

- `ytmo bootstrap` is create-only (non-destructive).
- `ytmo full-reset` is destructive and requires confirmation unless `--yes` is passed.
- `ytmo weekly-sync` requires completed bootstrap and will instruct if missing.

## Local workspace files

`.ytmo/` contains local mutable files:

- `config.toml`
- `bootstrap.json`
- `state.json`
- `managed_playlists.json`
- `data/*.json`

These are intentionally ignored from git.

## Troubleshooting

- `Auth file not found`:
  - confirm your auth JSON exists
  - ensure it is either at `<workspace>/browser.json` or passed via `--auth-file /absolute/path/to/browser.json`
  - auth generation guide: [ytmusicapi Browser Authentication](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)
- `Bootstrap has not been completed`: run `ytmo init --bootstrap` or `ytmo bootstrap`.
- API mode key error: set `OPENAI_API_KEY` or switch to `--mode manual`.

## Development

### Development install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Local repo install (maintainers/testing)

```bash
pipx install .
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Release Automation

PyPI publishing is automated via GitHub Actions:

- `.github/workflows/release-pypi.yml`: publishes on `v*` tags
- `.github/workflows/release-testpypi.yml`: manual TestPyPI publish

Required repository secrets:

- `PYPI_API_TOKEN`
- `TEST_PYPI_API_TOKEN`
