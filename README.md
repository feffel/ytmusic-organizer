# ytmusic-organizer

Organize your YouTube Music likes into practical playlists with a guided first-time setup and weekly incremental sync.

## Features

- Guided onboarding: `ytmo setup`
- Initial setup build is non-destructive (create/populate only)
- Colorful setup wizard UI (Rich when available)
- Setup resume after interruption/failure
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

1. Run guided setup:

```bash
ytmo setup
```

The wizard handles auth setup and writes auth to `<workspace>/browser.json` by default.
If you already have an auth file, pass it explicitly:

```bash
ytmo setup --auth-file /absolute/path/to/browser.json
```

2. For weekly updates:

```bash
ytmo sync
```

3. For full destructive rebuild:

```bash
ytmo reset --yes
```

## Commands

- `ytmo setup [--mode manual|api] [--auth-file PATH] [--non-interactive] [--plan-from-stdin] [--restart]`
- `ytmo sync [--mode manual|api] [--non-interactive] [--plan-from-stdin]`
- `ytmo reset [--yes] [--mode manual|api] [--non-interactive] [--plan-from-stdin]`
- `ytmo cleanup [--yes] [--local-only]`
- `ytmo preview [--plan PATH]`

Common option:

- `--workspace` (default `~/.ytmusic-organizer`)
- `--json` (machine-readable output; keeps default Rich output unchanged when omitted)

## Modes

### Manual mode (default)

The CLI exports song JSON and waits for your model response JSON on stdin:

- full flows write prompt to `~/.ytmusic-organizer/data/full_reset_prompt_filled.txt`
- weekly sync writes prompt to `~/.ytmusic-organizer/data/new_songs_prompt_filled.txt`
- provide model JSON by piping/pasting into stdin (Ctrl-D to submit)
- default workspace path is `~/.ytmusic-organizer` (override with `--workspace`)

Prompt templates are packaged in `ytmusic_organizer/prompts/`.

### API mode

Requires:

- `OPENAI_API_KEY`

Run with `--mode api` to auto-generate plan JSON.

## Safety and state

- `ytmo setup` is create-only (non-destructive).
- `ytmo reset` is destructive and requires confirmation unless `--yes` is passed.
- `ytmo sync` requires completed setup and will instruct if missing.
- `ytmo cleanup` deletes playlists managed by this tool and removes local managed artifacts.

## Local workspace files

`~/.ytmusic-organizer/` contains local mutable files by default:

- `config.toml`
- `bootstrap.json`
- `setup_state.json`
- `state.json`
- `managed_playlists.json`
- `data/*.json`

These are intentionally ignored from git.

`managed_playlists.json` now stores managed playlist IDs (schema v2) for safe deletion targeting.

## Troubleshooting

- `Auth file not found`:
  - run interactive setup: `ytmo setup`
  - or pass an existing file via `--auth-file /absolute/path/to/browser.json`
  - auth guide: [ytmusicapi Browser Authentication](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)
- `Setup has not been completed`: run `ytmo setup`.
- `Setup interrupted`: run `ytmo setup` to resume, or `ytmo setup --restart` to restart.
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

## Agent Automation

For AI/automation integration details (install, auth requirements, command contracts, and JSON output examples), see:

- [docs/automation.md](docs/automation.md)

## Release Automation

PyPI publishing is automated via GitHub Actions:

- `.github/workflows/release-pypi.yml`: publishes on `v*` tags
- `.github/workflows/release-testpypi.yml`: manual TestPyPI publish

Required repository secrets:

- `PYPI_API_TOKEN`
- `TEST_PYPI_API_TOKEN`
