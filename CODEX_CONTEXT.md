# Project Overview
`ytmusic-organizer` is a Python CLI tool that organizes YouTube Music liked songs into curated playlists.

It supports:
- guided first-time setup (`ytmo setup`)
- incremental weekly sync (`ytmo sync`)
- destructive rebuild (`ytmo reset`)
- cleanup (`ytmo cleanup`)
- local workspace reporting (`ytmo stats`)
- installed version output (`ytmo --version`)
- optional machine-readable command responses (`--json`)

Runtime state is workspace-centric: mutable files live under a workspace directory (default `~/.ytmusic-organizer/`).

# Core Workflows
## Weekly Sync
Primary entrypoint: `ytmo sync`.

Flow:
1. Load workspace config and auth.
2. Export only new likes via `export_new_likes(...)` by diffing current likes against `state.json` (`processed_video_ids`).
3. Classification step:
- Manual mode: writes `data/new_songs_prompt_filled.txt`, then reads plan JSON from stdin and saves `data/new_plan.json` (interactive entry auto-completes on valid JSON; blank line can submit raw/fenced attempts).
- API mode: calls OpenAI and writes `data/new_plan.json`.
4. Apply mapped songs to existing managed playlists via `apply_new_likes(...)`.
5. Update `state.json` with matched new video IDs.
6. Write unresolved items to `data/missing_matches.json`.

Implementation location:
- Orchestration: `ytmusic_organizer/workflows.py` (`run_weekly_sync`)
- Core ops: `ytmusic_organizer/ytmusic_ops.py`

## Full Reset
Primary entrypoint: `ytmo reset --yes`.

Flow:
1. Export full likes via `export_liked(...)` into `data/liked_songs.json`.
2. Classification step:
- Manual mode: writes `data/full_reset_prompt_filled.txt`, then reads plan JSON from stdin and saves `data/playlist_plan.json` (interactive entry auto-completes on valid JSON; blank line can submit raw/fenced attempts).
- API mode: calls OpenAI and writes `data/playlist_plan.json`.
3. Delete previously managed playlists via `delete_managed_playlists(...)` (ID-based targeting).
4. Recreate/populate playlists via `apply_plan(...)`.
5. Persist fresh managed playlist index from applied playlist IDs.
6. Reinitialize `state.json` from all current liked song IDs via `initialize_state(...)`.
7. Mark bootstrap complete in `bootstrap.json`.

Implementation location:
- Orchestration: `ytmusic_organizer/workflows.py` (`run_full_reset`)
- Core ops: `ytmusic_organizer/ytmusic_ops.py`

# Key Files
Note: below paths are workspace-relative (default `~/.ytmusic-organizer/`) unless explicitly noted.

- `browser.json`
Type: source/input secret auth file.
Used by `ytmusicapi` session creation. Must be preserved.
Interactive setup now accepts either raw `Header: value` lines or JSON-style header objects from browser tools, then normalizes before writing auth.

- `state.json`
Type: generated persistent state.
Schema: `{ "processed_video_ids": [...] }`.
Used to detect incremental new likes.

- `managed_playlists.json`
Type: generated persistent index.
Schema v2: `{ "schema_version": 2, "playlists": [{ "name": "...", "playlist_id": "..." }] }`.
Source of truth for which playlists this tool is allowed to delete/manage (by ID).

- `data/playlist_plan.json`
Type: generated or user-supplied plan artifact.
Produced by manual/API classification for full setup/reset.

- `data/new_plan.json`
Type: generated or user-supplied incremental plan artifact.
Produced by manual/API classification for weekly sync.

- `data/new_likes.json`
Type: generated intermediate artifact.
Contains only likes not yet in `state.json`.

- `data/liked_songs.json`
Type: generated intermediate artifact.
Full liked-song export snapshot at setup/reset time.

- `data/missing_matches.json`
Type: generated diagnostic artifact.
Songs from plan that could not be matched to source tracks.

- `bootstrap.json`
Type: generated guard marker.
`{ "completed": true }` is required before sync.

- `setup_state.json`
Type: generated resumable setup state.
Tracks per-step progress and last setup error.

- `config.toml`
Type: generated/editable local config.
Key values: `auth_file`, `classification_mode`, `openai_model`.

# Scripts
Implementation is module-based under `ytmusic_organizer/`.
Maintainer automation scripts live under `scripts/` and write outputs to ignored `artifacts/`.

- `ytmusic_organizer/ytmusic_ops.py::export_liked`
Reads: YouTube Music API liked songs.
Writes: `data/liked_songs.json`.

- `ytmusic_organizer/ytmusic_ops.py::export_new_likes`
Reads: YouTube Music API liked songs, `state.json`.
Writes: `data/new_likes.json`.

- `ytmusic_organizer/ytmusic_ops.py::apply_plan`
Reads: `data/liked_songs.json`, `data/playlist_plan.json`, existing library playlists.
Writes: playlist changes remotely; `data/missing_matches.json` locally.

- `ytmusic_organizer/ytmusic_ops.py::apply_new_likes`
Reads: `data/new_likes.json`, `data/new_plan.json`, `state.json`, existing library playlists.
Writes: playlist additions remotely; updates `state.json`; writes `data/missing_matches.json`.

- `ytmusic_organizer/ytmusic_ops.py::initialize_state`
Reads: `data/liked_songs.json`.
Writes: `state.json`.

- `ytmusic_organizer/ytmusic_ops.py::delete_managed_playlists`
Reads: `managed_playlists.json`, current library playlists.
Writes: remote playlist deletions by playlist ID only; legacy name-only entries are skipped conservatively.

- `ytmusic_organizer/ytmusic_ops.py::update_managed_playlists`
Reads: `data/playlist_plan.json`.
Writes: `managed_playlists.json`.

- `ytmusic_organizer/workflows.py`
Orchestration for setup/sync/reset/cleanup/stats.

- `ytmusic_organizer/cli.py`
Command parsing and user-facing flow control.
Supports optional JSON output mode (`--json`) for automation.

- `ytmusic_organizer/matching.py`
Title/artist normalization and matching heuristics.

- `ytmusic_organizer/validation.py`
Strict schema checks for plan JSON.

- `ytmusic_organizer/planning.py`
Prompt rendering, manual stdin JSON intake, OpenAI API classification.

- `scripts/demo/record.sh`, `scripts/demo/render.sh`, `scripts/demo/validate.sh`
Demo capture/render/validation helpers. Outputs go to `artifacts/demo/` and are not committed.

- `scripts/launch/generate.sh`
Generates launch input bundle (`project-metadata.json`, `CHANGELOG.md`, `stats.json`) in `artifacts/launch/<timestamp>/` for private launch orchestration.

# Shell Workflows
No dedicated shell wrapper scripts are used.

Canonical execution paths:
1. Direct CLI via `ytmo ...` (or `python -m ytmusic_organizer.cli ...`).
2. `make` targets that delegate to the CLI.

# Make Targets
Current `Makefile` targets are:
- `make setup` -> `ytmo setup`
- `make sync` -> `ytmo sync`
- `make reset` -> `ytmo reset`
- `make cleanup` -> `ytmo cleanup`
- `make stats` -> `ytmo stats` (supports optional `--plan PATH` diagnostics input)
- `make test` -> run unit tests
- `make demo-record` -> record CLI demo cast to ignored artifacts
- `make demo-render` -> render demo gif/mp4 from cast
- `make demo-check` -> fail when `.cast/.gif/.mp4` files are tracked in git
- `make launch-generate` -> generate launch input bundle under ignored artifacts

Makefile execution detail:
- All targets run through `.venv/bin/python` and require `.venv` to exist.
- `check-venv` guard fails fast with setup instructions if `.venv` is missing.

Automation docs:
- `docs/automation.md` is the integration contract for agents/scripts (non-interactive flags, stdin manual mode, JSON output shape).

Release automation:
- `.github/workflows/release-pypi.yml` publishes on `v*` tags using Trusted Publishing (OIDC).
- `.github/workflows/release-pypi.yml` also creates a GitHub Release with autogenerated notes and attaches `dist/*`.
- `.github/workflows/release-testpypi.yml` publishes manually to TestPyPI using Trusted Publishing (OIDC).
- No PyPI token secrets are required when trusted publisher bindings are configured on PyPI/TestPyPI.

CI automation:
- `.github/workflows/ci.yml` runs tests (3.11/3.12/3.13), package build + `twine check`, `pipx` CLI smoke checks, and repo media guards.

# Data Flow
## `data/liked_songs.json`
- Created during setup/reset.
- Represents full snapshot of liked songs.
- Input to full-plan matching and state initialization.

## `data/new_likes.json`
- Created during sync by subtracting `state.json` IDs from current likes.
- Empty file (`[]`) means no incremental work.

## `data/playlist_plan.json`
- Full classification plan from manual/API step.
- Input to managed playlist index generation and playlist application.

## `state.json`
- Initialized from full liked snapshot during setup/reset.
- Incrementally updated in sync with matched new IDs.
- Monotonic growth in normal weekly usage; reset rewrites from fresh full export.

## `data/new_plan.json`
- Incremental classification plan for only `new_likes.json` items.
- Consumed by `apply_new_likes` and can be overwritten each sync cycle.

## `data/missing_matches.json`
- Rewritten each apply run with current unresolved mapping items.

# Safety Rules
- Only delete playlists whose IDs are listed in `managed_playlists.json` schema v2.
- Never delete arbitrary playlists outside managed index.
- Do not overwrite or expose `browser.json`.
- Interactive auth setup captures paste in non-canonical TTY mode (to avoid long-line truncation), and both TTY/non-TTY now share one header-collection state machine: auto-detect JSON-vs-raw input, complete on closing `}` (JSON) or blank line (raw), and validate required keys (`cookie`, `x-goog-authuser`) before writing auth.
- Interactive manual plan input no longer depends on EOF signals; it accepts line-based paste, auto-submits once JSON parses, and allows blank-line submit for raw/fenced retries.
- `state.json` should only grow during incremental sync; full reset intentionally reinitializes it.
- `ytmo reset` and `ytmo cleanup` are destructive by design and require explicit confirmation unless `--yes` is passed.
- `ytmo setup` is non-destructive for existing remote playlists (create/populate only).
- `ytmo stats` is non-failing for local artifact issues and reports diagnostics/warnings instead of failing.
- `ytmo stats` is read-only and does not rewrite `data/missing_matches.json`.
- Generated demo media (`.cast/.gif/.mp4`) must never be committed; only scripts/docs are tracked.

# Known Limitations
- Matching heuristics are text-based (`title_match` + `artist_match`) and may produce loose/ambiguous misses.
- Manual classification remains required in default mode; automation depends on OpenAI API mode.
- Correctness depends on YTMusic API response structure and metadata quality.
- `apply_new_likes` updates `state.json` with matched IDs only (unmatched IDs remain unprocessed and can reappear in later syncs).
- Running commands with different `--workspace` values creates separate state trees; operators must stay consistent.
- Legacy managed playlist files without schema v2 are not auto-deleted for safety.

# Improvement Ideas
- Add Make aliases `weekly-sync` and `full-reset` (or document naming migration in CLI help output).
- Add explicit versioned JSON schemas for plan/state files and validate on every read.
- Add idempotency markers/history for sync runs (timestamps, counts, run IDs).
- Add optional quarantine flow for unmatched new likes to avoid repeated manual rematching.
- Add dry-run mode for reset/cleanup showing exact playlists that would be deleted.
- Add tests covering full sync/reset orchestration with fixture workspaces.
- Harden matching by incorporating album/duration similarity scoring.

# Maintenance Rule For Future Codex Runs
If repository changes affect workflows, scripts/modules, file structure, data flow, commands, or dependencies, update this file in the same change.

Required behavior:
- Keep this file as canonical high-level project memory.
- Preserve historical context unless it is no longer accurate.
- When behavior changes, update the corresponding section(s) immediately.
