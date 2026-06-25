# Reference

This page keeps detailed usage and maintainer-oriented details out of the main README.

## Commands

- `ytmo setup [--mode manual|api] [--auth-file PATH] [--auth-method auto|browser|manual] [--non-interactive] [--restart] [--dry-run]`
- `ytmo sync [--mode manual|api] [--non-interactive] [--dry-run]`
- `ytmo rebuild [--yes] [--mode manual|api] [--non-interactive] [--dry-run]`
- `ytmo cleanup [--yes] [--local-only] [--dry-run]`
- `ytmo demo [--mode manual|api]`
- `ytmo stats [--plan PATH]`

Shared options:

- `--workspace` (default: `~/.ytmusic-organizer`) is available on every subcommand.
- `--json` is available on `setup`, `sync`, `rebuild`, `cleanup`, and `stats`.
- `--dry-run` is available on `setup`, `sync`, `rebuild`, and `cleanup`; it may still require auth/network reads.
- `--version` is top-level only.

## Modes

`manual` mode:
- No API cost.
- You provide plan JSON output each run.
- Writes prompt files in workspace:
  - `data/full_reset_prompt_filled.txt`
  - `data/new_songs_prompt_filled.txt`
- In an interactive terminal, pasted JSON auto-submits once it parses; raw/fenced retries can be submitted with a blank line.

`api` mode:
- Auto-generates plan JSON through OpenAI API.
- Requires `OPENAI_API_KEY`.

## Auth Setup

`ytmo setup` creates `browser.json` from browser request headers.

Auth methods:
- `auto` (default): open YouTube Music and capture authenticated browser traffic; fall back to manual paste if capture fails.
- `browser`: require browser capture and fail if it cannot capture auth.
- `manual`: skip browser capture and paste request headers.

Browser capture uses a tool-owned browser profile in the workspace. Setup tells you to log in to YouTube Music if needed, keeps waiting for an authenticated request, and tries to bring the browser page forward. If Chromium is missing, interactive setup asks before installing the required Playwright browser automatically.

After setup has completed, interactive `ytmo sync` also repairs a missing configured auth file with the same browser-first flow before continuing. This is only an auth repair path; it does not replace first-time `ytmo setup`, because sync depends on setup-created state and managed-playlist artifacts. Non-interactive sync and all dry-runs require an existing readable auth file.

Long-running network, browser, playlist, and classification steps show a wait indicator in human output. JSON output stays machine-readable and does not include wait text.

Troubleshooting: if setup reports that the Python `playwright` package is unavailable, reinstall or upgrade `ytmusic-organizer` so its runtime environment includes declared dependencies.

Accepted paste formats:
- Raw header lines, submitted with one blank line:
  - `cookie: <value>`
  - `x-goog-authuser: 1`
- JSON-style header objects copied from browser tools:
  - `{"cookie":"<value>","x-goog-authuser":"1",...}`

Required keys:
- `cookie`
- `x-goog-authuser`

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

`ytmo cleanup` removes generated managed artifacts only: `state.json`, `managed_playlists.json`, setup markers, plan/likes/missing-match files, and filled prompt files. It does not remove `config.toml` or `browser.json`.

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
- `make pr-ready` is an alias of `make verify` for PR readiness checks.
- `make hooks-install` installs both `pre-commit` and `pre-push` hooks.

## Release and Automation

- Automation contract: [automation.md](automation.md)
- Collaborator workflows (demo/release scripts): [collaborators.md](collaborators.md)

Release workflows:
- `.github/workflows/release-pypi.yml`
- `.github/workflows/release-testpypi.yml`
- `.github/workflows/dependency-review.yml`
