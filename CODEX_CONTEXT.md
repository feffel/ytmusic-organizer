# Project Overview
`ytmusic-organizer` is a Python CLI tool that organizes YouTube Music liked songs into curated playlists.

It supports:
- guided first-time setup (`ytmo setup`)
- incremental weekly sync (`ytmo sync`)
- destructive rebuild (`ytmo rebuild`)
- cleanup (`ytmo cleanup`)
- local workspace reporting (`ytmo stats`)
- installed version output (`ytmo --version`)
- optional machine-readable command responses (`--json`)
- safe simulation mode (`--dry-run`) for setup/sync/rebuild/cleanup

Runtime state is workspace-centric: mutable files live under a workspace directory (default `~/.ytmusic-organizer/`).

# Core Workflows
## Weekly Sync
Primary entrypoint: `ytmo sync`.

Flow:
1. Load workspace config and auth.
2. Export only new likes via `export_new_likes(...)` by diffing current likes against `state.json` (`processed_video_ids`).
3. Classification step:
- Manual mode: writes `data/new_songs_prompt_filled.txt`, then reads plan JSON input and saves `data/new_plan.json` (interactive entry auto-completes on valid JSON; blank line can submit raw/fenced attempts).
- API mode: calls OpenAI and writes `data/new_plan.json`.
4. Apply mapped songs to existing managed playlists via `apply_new_likes(...)`.
5. Update `state.json` with matched new video IDs.
6. Write unresolved items to `data/missing_matches.json`.

Implementation location:
- Orchestration: `ytmusic_organizer/workflows.py` (`run_weekly_sync`)
- Core ops: `ytmusic_organizer/ytmusic_ops.py`

## Full Rebuild
Primary entrypoint: `ytmo rebuild --yes`.

Flow:
1. Export full likes via `export_liked(...)` into `data/liked_songs.json`.
2. Classification step:
- Manual mode: writes `data/full_reset_prompt_filled.txt`, then reads plan JSON input and saves `data/playlist_plan.json` (interactive entry auto-completes on valid JSON; blank line can submit raw/fenced attempts).
- API mode: calls OpenAI and writes `data/playlist_plan.json`.
3. Delete previously managed playlists via `delete_managed_playlists(...)` (ID-based targeting).
4. Recreate/populate playlists via `apply_plan(...)`.
5. Persist fresh managed playlist index from applied playlist IDs.
6. Reinitialize `state.json` from all current liked song IDs via `initialize_state(...)`.
7. Mark bootstrap complete in `bootstrap.json`.

Implementation location:
- Orchestration: `ytmusic_organizer/workflows.py` (`run_full_reset`)
- Core ops: `ytmusic_organizer/ytmusic_ops.py`

## Workspace Stats
Primary entrypoint: `ytmo stats`.

Flow:
1. Read local workspace artifacts (`state.json`, managed index, likes snapshots, plans, missing matches).
2. Run non-failing diagnostics for malformed/missing artifacts.
3. Optionally validate/diagnose plan quality against `data/liked_songs.json`.
4. Derive local insights (`identity_score`, richer top playlist summaries, `coverage_ratio`, collection/momentum labels).
5. Render human output via a TTY-first single-canvas diagnostics dashboard (`Status Overview`, `Plan & Coverage`, `Playlist Standings`) or plain grouped text when not in TTY. Stats output is diagnostics/action oriented; vague narrative rows are intentionally omitted.

Implementation location:
- Orchestration and insight derivation: `ytmusic_organizer/workflows.py` (`run_stats`)
- Presentation and animation primitives: `ytmusic_organizer/ui.py` (`WizardUI.show_stats`)

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
Produced by manual/API classification for full setup/rebuild.

- `data/new_plan.json`
Type: generated or user-supplied incremental plan artifact.
Produced by manual/API classification for weekly sync.

- `data/new_likes.json`
Type: generated intermediate artifact.
Contains only likes not yet in `state.json`.

- `data/liked_songs.json`
Type: generated intermediate artifact.
Full liked-song export snapshot at setup/rebuild time.

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
Notes: uses unbounded API fetch (`limit=None`) to avoid silent truncation on large libraries.

- `ytmusic_organizer/ytmusic_ops.py::export_new_likes`
Reads: YouTube Music API liked songs, `state.json`.
Writes: `data/new_likes.json`.
Notes: tolerates malformed `state.json` by falling back to empty processed set.

- `ytmusic_organizer/ytmusic_ops.py::apply_plan`
Reads: `data/liked_songs.json`, `data/playlist_plan.json`, existing library playlists.
Writes: playlist changes remotely; `data/missing_matches.json` locally.

- `ytmusic_organizer/ytmusic_ops.py::apply_new_likes`
Reads: `data/new_likes.json`, `data/new_plan.json`, `state.json`, existing library playlists.
Writes: playlist additions remotely; updates `state.json`; writes `data/missing_matches.json`.
Notes: tolerates malformed `state.json` by resetting to default structure.

- `ytmusic_organizer/ytmusic_ops.py::initialize_state`
Reads: `data/liked_songs.json`.
Writes: `state.json`.

- `ytmusic_organizer/ytmusic_ops.py::delete_managed_playlists`
Reads: `managed_playlists.json`, current library playlists.
Writes: remote playlist deletions by playlist ID only; legacy name-only entries are skipped conservatively.
Notes: library and playlist reads now use unbounded fetch (`limit=None`).

- `ytmusic_organizer/ytmusic_ops.py::simulate_delete_managed_playlists`
Reads: `managed_playlists.json`, optionally current library playlists.
Writes: none (returns would-delete counts for dry-run).

- `ytmusic_organizer/ytmusic_ops.py::update_managed_playlists`
Reads: `data/playlist_plan.json`.
Writes: `managed_playlists.json`.

- `ytmusic_organizer/workflows.py`
Orchestration for setup/sync/rebuild/cleanup/stats, dry-run simulation paths, terminal-only demo simulation, and stats insight derivation.
Setup now persists `config.toml` only after auth is confirmed, so failed auth does not produce misleading "workspace ready" completion state.

- `ytmusic_organizer/cli.py`
Command parsing and user-facing flow control.
Supports optional JSON output mode (`--json`) for automation and command recaps/callouts for human output.

- `ytmusic_organizer/ui.py`
TTY-first flow renderer. Provides guided stepper surfaces for command workflows, modern recap/callout cards, dry-run preview cards, and a single-canvas staged stats renderer for interactive terminals. Rich/TTY output also applies dedicated path accent styling for filesystem paths across step/detail/callout/recap surfaces. UI now uses a softened Neon Stage visual theme (cool cyan-led accents for non-error surfaces, red reserved for actual errors, music-flavored icons/waveform cues in rich mode, and deterministic plain-text tags like `[stage]`, `[beat]`, `[drop]`, `[encore]` in non-TTY mode).

- `ytmusic_organizer/matching.py`
Title/artist normalization and matching heuristics.

- `ytmusic_organizer/validation.py`
Strict schema checks for plan JSON.

- `ytmusic_organizer/planning.py`
Prompt rendering, manual JSON input intake, OpenAI API classification.

- `scripts/demo/record.sh`, `scripts/demo/render.sh`, `scripts/demo/validate.sh`
Demo capture/render/validation helpers. `record.sh` records an optional raw cast to ignored `artifacts/demo/`. `render.sh` now renders the scripted demo session with `vhs`, writes ignored outputs under `artifacts/demo/`, and refreshes the tracked README asset at `docs/assets/demo.gif`.

- `scripts/launch/generate.sh`
Generates launch input bundle (`project-metadata.json`, `CHANGELOG.md`, `stats.json`) in `artifacts/launch/<timestamp>/` for private launch orchestration.

# Shell Workflows
Canonical execution paths:
1. Direct CLI via `ytmo ...` (or `python -m ytmusic_organizer.cli ...`).
2. `make` targets that delegate to the CLI.
3. `make` verification targets for pre-push/PR readiness.

# Make Targets
Current `Makefile` targets are:
- `make setup` -> `ytmo setup`
- `make sync` -> `ytmo sync`
- `make rebuild` -> `ytmo rebuild`
- `make cleanup` -> `ytmo cleanup`
- `ytmo demo` -> simulation-only setup walkthrough (`--mode manual|api`), no remote/local side effects
- `make stats` -> `ytmo stats` (supports optional `--plan PATH` diagnostics input)
- `make test` -> run unit tests
- `make verify` -> run lint (`ruff check`), format check (`ruff format --check`), and unit tests
- `make pr-ready` -> alias of `make verify` for PR readiness checks
- `make hooks-install` -> install local `pre-commit` and `pre-push` hooks
- `make demo-record` -> record CLI demo cast to ignored artifacts
- `make demo-render` -> render demo gif/mp4 from scripted demo session and refresh `docs/assets/demo.gif`
- `make demo-check` -> fail when `.cast/.gif/.mp4` files are tracked in git
- `make launch-generate` -> generate launch input bundle under ignored artifacts

Makefile execution detail:
- All targets run through `.venv/bin/python` and require `.venv` to exist.
- `check-venv` guard fails fast with setup instructions if `.venv` is missing; setup guidance installs editable package with dev extras (`pip install -e .[dev]`) so `ruff`/`pre-commit` targets work.

Documentation split:
- `README.md` is intentionally short and optimized for discoverability + first run, and now embeds the tracked demo asset at `docs/assets/demo.gif`.
- `docs/reference.md` holds detailed CLI/options/modes/workspace/troubleshooting/development reference.
- `docs/automation.md` is the integration contract for agents/scripts (non-interactive flags, manual-mode input behavior, JSON output shape).
- `docs/collaborators.md` is collaborator-only guidance (demo asset generation, launch/release/CI workflow pointers).

Release automation:
- `.github/workflows/release-pypi.yml` publishes on `v*` tags (and manual dispatch) using Trusted Publishing (OIDC).
- `.github/workflows/release-pypi.yml` also creates a GitHub Release with autogenerated notes and attaches `dist/*`.
- `.github/workflows/release-testpypi.yml` publishes manually to TestPyPI using Trusted Publishing (OIDC).
- No PyPI token secrets are required when trusted publisher bindings are configured on PyPI/TestPyPI.
- Release/CI package-build steps delete `dist/` and `build/` before `python -m build` so stale artifacts cannot be republished.

CI automation:
- `.github/workflows/ci.yml` runs lint (`ruff`, `pre-commit`), tests (3.11/3.12/3.13), package build + `twine check`, `pipx` CLI smoke checks, and repo media guards.
- `.github/workflows/ci.yml` triggers on pull requests and on pushes to `main` only (avoids duplicate feature-branch push + PR runs).
- CI uses `uv` for Python dependency installation and includes workflow concurrency cancellation.
- `.github/workflows/dependency-review.yml` runs dependency risk checks on pull requests.
- `.github/dependabot.yml` keeps pip and GitHub Actions dependencies updated weekly.

Local quality gates:
- `.pre-commit-config.yaml` includes a `pre-push` hook that runs `make verify`.
- Install with `make hooks-install`.

Repository hygiene:
- `dist/` and `build/` are local packaging outputs and must remain untracked.

# Data Flow
## `data/liked_songs.json`
- Created during setup/rebuild.
- Represents full snapshot of liked songs.
- Input to full-plan matching and state initialization.

## `data/new_likes.json`
- Created during sync by subtracting `state.json` IDs from current likes.
- Empty file (`[]`) means no incremental work.

## `data/playlist_plan.json`
- Full classification plan from manual/API step.
- Input to managed playlist index generation and playlist application.

## `state.json`
- Initialized from full liked snapshot during setup/rebuild.
- Incrementally updated in sync with matched new IDs.
- Monotonic growth in normal weekly usage; rebuild rewrites from fresh full export.

## `data/new_plan.json`
- Incremental classification plan for only `new_likes.json` items.
- Consumed by `apply_new_likes` and can be overwritten each sync cycle.

## `data/missing_matches.json`
- Rewritten each apply run with current unresolved mapping items.

## `run_stats` derived insights
- `run_stats` computes local-only derived insight fields: `identity_score`, `plan_playlists`, `top_playlists`, `coverage_ratio`, `collection_shape`, and `pending_momentum`.
- `top_playlists` contains up to three ranked playlist summaries with name, song count, optional description, and up to three sample songs.
- `run_stats` also includes additive fields for human diagnostics: `artifact_paths`, `missing_required_artifacts`, and `managed_playlist_names`.
- These are included in command results and power human stats rendering; JSON output remains backward-compatible.

# Safety Rules
- Only delete playlists whose IDs are listed in `managed_playlists.json` schema v2.
- Never delete arbitrary playlists outside managed index.
- Do not overwrite or expose `browser.json`.
- Interactive auth setup captures paste in non-canonical TTY mode (to avoid long-line truncation), and both TTY/non-TTY now share one header-collection state machine: auto-detect JSON-vs-raw input, complete on closing `}` (JSON) or blank line (raw), and validate required keys (`cookie`, `x-goog-authuser`) before writing auth.
- Setup writes `config.toml` transactionally after auth is ready; missing auth no longer emits a premature workspace-ready success line.
- Interactive manual plan input no longer depends on EOF signals; it accepts line-based paste, auto-submits once JSON parses, and allows blank-line submit for raw/fenced retries.
- Manual classification callouts now explicitly instruct users to run the generated prompt in their AI tool and paste back the full output JSON.
- Human-facing CLI output uses a TTY-first renderer with guided stepper progress for setup/sync/rebuild/demo, recap cards for command completion, and callout-style confirmations.
- Human-facing CLI output follows the Neon Stage theme across surfaces while remaining pure CLI (no full-screen TUI): rich mode uses icon-accented lines/cards plus waveform/queue cues and stats-section music markers, while plain mode uses stable ASCII tags so logs stay script-friendly.
- Human-facing copy includes optional music-inspired microcopy with dry, gentle sarcasm, injected additively only (never replacing actionable core text).
- Easter-egg microcopy slots: `flow_info`, `flow_success`, `warning_suffix`, `recap_footer`, `stats_narrative`. Stats rendering no longer uses `stats_narrative`; the slot remains for backward-compatible internal copy inventory.
- Microcopy appearance is true-random per eligible slot, default probability `0.12`, configurable via `YTMO_MICROCOPY_PROBABILITY` (or `YTMO_MICROCOPY_PROB`), clamped to `[0.0, 1.0]`.
- UI theming is now fixed to the `indigo-vinyl` palette by default (no runtime theme knob), keeping contrast stable and avoiding color-state ambiguity across terminals.
- Top-level CLI interruption handling is traceback-safe: `KeyboardInterrupt`/`EOFError` return user-facing guidance instead of uncaught tracebacks.
- Setup interruption guidance is rendered as a styled warning callout (`Setup interrupted`) in human mode, while JSON mode keeps machine-readable error payloads.
- CLI parse/usage errors now print scoped help with exit code `2`: top-level parse failures show top-level help, while subcommand parse failures (for example `ytmo setup -q`) show that subcommand’s help. Implementation uses a custom `ArgumentParser.error()` override and applies that parser class to subparsers, so `choices=` validation (for example `--mode`) also routes through scoped help. A `SystemExit(2)` fallback in `main()` preserves scoped-help behavior on Python `3.11` paths where argparse can still exit early despite `exit_on_error=False`.
- All human-mode command interruptions now use styled warning callouts (`Operation cancelled`) with a forced leading newline so shell `^C` echoes do not collide with callout content.
- Setup interruption callout rendering now prints a leading newline before the panel so shell `^C` echoes do not collide with the callout title.
- Rich callouts now apply line-level emphasis: heading lines (ending with `:`) are bolded and suggested command lines (for example `ytmo ...`) are highlighted with the command accent color for faster scanning.
- Non-TTY/plain callouts preserve raw body lines (no `[warning]/[info]` prefixes), so suggested shell commands remain copy/paste-safe in redirected output and logs.
- Interactive setup mode-selection prompt interruption (Ctrl-C/Ctrl-D) now raises the same setup-specific resume guidance (`Setup was interrupted...`) as later setup steps.
- Resumable setup now replays previously completed setup steps as numbered `Step n/6 done ...` entries so resumed runs keep accurate step index progression instead of muted `Resuming:` notes.
- Interactive resumed setup no longer re-prompts for default classification mode when no `--mode` override is passed; it reuses persisted `classification_mode`.
- Interactive TTY stats output is diagnostics-first and rendered as one strong-border canvas with internal section separators. Reveal choreography is fixed to 0.25s (overview), 0.18s (plan/coverage), 0.18s (playlist standings), 0.12s (health), then frame lock.
- Non-TTY output stays deterministic plain text with the same information hierarchy.
- `--json` output remains machine-stable.
- `state.json` should only grow during incremental sync; full rebuild intentionally reinitializes it.
- `run_stats` is now read-only and does not create workspace directories.
- Core state/config/plan writes use atomic write-then-replace to reduce partial-write corruption risk.
- `cleanup` now removes local artifacts even when auth is missing; remote deletion is skipped and reported as a warning field.
- `ytmo rebuild` and `ytmo cleanup` are destructive by design and require explicit confirmation unless `--yes` is passed.
- `ytmo setup` is non-destructive for existing remote playlists (create/populate only).
- `--dry-run` for setup/sync/rebuild/cleanup performs read-only simulation: no remote playlist mutations and no workspace writes, but auth and network reads may still be required.
- Manual-mode dry-run writes prompt text only to temporary files outside workspace and auto-deletes them.
- `ytmo demo` is always simulation-only: no auth setup, no YTMusic/OpenAI calls, no playlist mutations, and no workspace writes.
- `ytmo stats` is non-failing for local artifact issues and reports diagnostics/warnings instead of failing.
- `ytmo stats` human output maps internal plan status codes to friendly labels and keeps overall status plus diagnostics compact in `Status Overview`.
- `ytmo stats` health treats only core setup artifacts as required (`config.toml`, `state.json`, `managed_playlists.json`, `data/liked_songs.json`, `data/playlist_plan.json`). Sync-cycle artifacts (`data/new_likes.json`, `data/new_plan.json`, `data/missing_matches.json`) do not make a completed setup appear incomplete.
- `ytmo stats` shows the path to `data/missing_matches.json` when unresolved matches exist, and `Playlist Standings` renders top-three playlists as a wrapped three-column podium (`Silver | Gold | Bronze`) with wrapped samples, honorable mentions, and compact diagnostics below it.
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
- Add Make aliases `weekly-sync` and `full-rebuild` (or document naming migration in CLI help output).
- Add explicit versioned JSON schemas for plan/state files and validate on every read.
- Add idempotency markers/history for sync runs (timestamps, counts, run IDs).
- Add optional quarantine flow for unmatched new likes to avoid repeated manual rematching.
- Add tests covering full sync/rebuild orchestration with fixture workspaces.
- Harden matching by incorporating album/duration similarity scoring.

# Maintenance Rule For Future Codex Runs
If repository changes affect workflows, scripts/modules, file structure, data flow, commands, or dependencies, update this file in the same change.

Required behavior:
- Keep this file as canonical high-level project memory.
- Preserve historical context unless it is no longer accurate.
- When behavior changes, update the corresponding section(s) immediately.
