# ytmusic-organizer

[![PyPI](https://img.shields.io/pypi/v/ytmusic-organizer?label=PyPI&color=0A7BBB)](https://pypi.org/project/ytmusic-organizer/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/ytmusic-organizer/)
[![License](https://img.shields.io/pypi/l/ytmusic-organizer?color=6aa84f)](https://github.com/feffel/ytmusic-organizer/blob/main/LICENSE)
[![CI](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml)
[![PyPI Publish](https://github.com/feffel/ytmusic-organizer/actions/workflows/release-pypi.yml/badge.svg)](https://github.com/feffel/ytmusic-organizer/actions/workflows/release-pypi.yml)

Organize your YouTube Music likes into practical playlists with a guided first-time setup and weekly incremental sync.

```text
            ██╗   ██╗████████╗███╗   ███╗ ██████╗
            ╚██╗ ██╔╝╚══██╔══╝████╗ ████║██╔═══██╗
             ╚████╔╝    ██║   ██╔████╔██║██║   ██║
              ╚██╔╝     ██║   ██║╚██╔╝██║██║   ██║
               ██║      ██║   ██║ ╚═╝ ██║╚██████╔╝
               ╚═╝      ╚═╝   ╚═╝     ╚═╝ ╚═════╝

            Y T M O  •  Playlist Automation, Human Taste.
```

## Features

- Turn a large liked-songs library into usable playlists fast.
- Keep playlists continuously fresh as your taste changes week to week.
- Save hours of manual sorting and repetitive playlist maintenance.
- Rebuild your playlist structure anytime.
- Keep full control over classification with either manual or API-driven workflows.
- Run reliably in terminal or automation with the same command surface.

## Install

### Recommended (PyPI)

```bash
pipx install ytmusic-organizer
```

### From GitHub (if you prefer source install)

```bash
pipx install git+https://github.com/feffel/ytmusic-organizer.git
```

## Demo

Demo media is hosted as GitHub Release assets and referenced here:

- Demo GIF: `https://github.com/feffel/ytmusic-organizer/releases/latest`

Demo generation scripts are in-repo, but generated media is never committed.
See [docs/demo.md](docs/demo.md).

## Who This Is For

Good fit:
- You like songs in YouTube Music and want them organized into reusable playlists.
- You are too busy (or too lazy) to hand-curate playlists manually.
- You want a repeatable weekly sync workflow.
- You are comfortable running a CLI.

Not a fit:
- You need fully automatic playlist strategy generation without any manual/API classification step.
- You need cloud-hosted multi-user service behavior.

## Quickstart

1. Run guided setup:

```bash
ytmo setup
```

Safety model:
- This tool only deletes playlists tracked in `managed_playlists.json` (by playlist ID).
- `reset` and `cleanup` are destructive and require explicit confirmation unless `--yes` is passed.

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

Typical weekly commands:

Manual mode:
```bash
ytmo sync --mode manual
```

API mode:
```bash
ytmo sync --mode api
```

## Commands

- `ytmo setup [--mode manual|api] [--auth-file PATH] [--non-interactive] [--restart]`
- `ytmo sync [--mode manual|api] [--non-interactive]`
- `ytmo reset [--yes] [--mode manual|api] [--non-interactive]`
- `ytmo cleanup [--yes] [--local-only]`
- `ytmo preview [--plan PATH]` (requires `data/liked_songs.json` plus a full plan JSON)
- `ytmo stats`

Common option:

- `--workspace` (default `~/.ytmusic-organizer`)
- `--json` (machine-readable output; keeps default Rich output unchanged when omitted)
- `--version` (print installed CLI version)

`--json` example:

```bash
ytmo sync --mode api --json
# {"status":"ok","command":"sync","result":{"new_likes":3,"missing":1,"processed":3}}
```

## Modes

### Manual mode (default)

The CLI exports song JSON and waits for your model response JSON on stdin:

- full flows write prompt to `~/.ytmusic-organizer/data/full_reset_prompt_filled.txt`
- weekly sync writes prompt to `~/.ytmusic-organizer/data/new_songs_prompt_filled.txt`
- provide model JSON by piping/pasting into stdin
- interactive paste auto-submits when closing braces are complete; otherwise submit with one blank line
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
- `ytmo preview` is diagnostic but writes `data/missing_matches.json` as output.

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
- `Preview prerequisites are missing`:
  - ensure `data/playlist_plan.json` exists (or pass `--plan /absolute/path/to/plan.json`)
  - ensure `data/liked_songs.json` exists (run `ytmo setup` or `ytmo reset --yes` to generate it)

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

Demo workflow and policy checks:

```bash
make demo-record
make demo-render
make demo-check
```

## Agent Automation

For AI/automation integration details (install, auth requirements, command contracts, and JSON output examples), see:

- [docs/automation.md](docs/automation.md)

## Release Automation

PyPI publishing is automated via GitHub Actions:

- `.github/workflows/release-pypi.yml`: publishes on `v*` tags
- `.github/workflows/release-testpypi.yml`: manual TestPyPI publish
- release workflow also creates a GitHub Release with autogenerated notes and attached `dist/*` artifacts

Publishing auth model:

- Uses PyPI/TestPyPI Trusted Publishing (OIDC) from GitHub Actions.
- No `PYPI_API_TOKEN`/`TEST_PYPI_API_TOKEN` repository secrets are required.
- PyPI/TestPyPI project must have matching trusted publisher configuration for this repository/workflow.
