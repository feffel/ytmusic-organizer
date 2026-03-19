# Reference

This page keeps detailed usage and maintainer-oriented details out of the main README.

## Commands

- `ytmo setup [--mode manual|api] [--auth-file PATH] [--non-interactive] [--restart] [--dry-run]`
- `ytmo sync [--mode manual|api] [--non-interactive] [--dry-run]`
- `ytmo rebuild [--yes] [--mode manual|api] [--non-interactive] [--dry-run]`
- `ytmo cleanup [--yes] [--local-only] [--dry-run]`
- `ytmo demo [--mode manual|api]`
- `ytmo stats [--plan PATH]`

Common options:

- `--workspace` (default: `~/.ytmusic-organizer`)
- `--json` (machine-readable output)
- `--dry-run` (non-mutating simulation; may still require auth/network reads)
- `--version`

## Modes

`manual` mode:
- No API cost.
- You provide plan JSON output each run.
- Writes prompt files in workspace:
  - `data/full_reset_prompt_filled.txt`
  - `data/new_songs_prompt_filled.txt`

`api` mode:
- Auto-generates plan JSON through OpenAI API.
- Requires `OPENAI_API_KEY`.

## Workspace Artifacts

Default mutable workspace: `~/.ytmusic-organizer/`

Primary artifacts:
- `config.toml`
- `bootstrap.json`
- `setup_state.json`
- `state.json`
- `managed_playlists.json`
- `data/liked_songs.json`
- `data/new_likes.json`
- `data/playlist_plan.json`
- `data/new_plan.json`
- `data/missing_matches.json`

## Troubleshooting

`Auth file not found`:
- Run `ytmo setup`
- Or pass `--auth-file /absolute/path/to/browser.json`
- Auth guide: <https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html>

`Setup has not been completed`:
- Run `ytmo setup`

`Setup interrupted`:
- Resume: `ytmo setup`
- Restart: `ytmo setup --restart`

`OPENAI_API_KEY is required for --mode api`:
- Set `OPENAI_API_KEY`
- Or run with `--mode manual`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
make hooks-install
make verify
make pr-ready
```

Notes:
- `make verify` runs `ruff check`, `ruff format --check`, and unit tests.
- `make pr-ready` verifies branch ancestry against the latest default branch on the resolved base remote (explicit arg/env -> `upstream` -> branch upstream remote -> push remote -> `origin`) then runs full `verify`.
- `make hooks-install` installs both `pre-commit` and `pre-push` hooks.

## Release and Automation

- Automation contract: [automation.md](automation.md)
- Collaborator workflows (demo/release scripts): [collaborators.md](collaborators.md)

Release workflows:
- `.github/workflows/release-pypi.yml`
- `.github/workflows/release-testpypi.yml`
- `.github/workflows/dependency-review.yml`
