# Automation Integration Guide

This guide describes how agents/scripts should install and run `ytmusic-organizer` reliably.

## Install

Preferred:

```bash
pipx install ytmusic-organizer
```

From source:

```bash
pipx install .
```

## Preconditions

- YouTube Music auth must exist at the configured auth path (default workspace `browser.json`).
- For API classification mode, `OPENAI_API_KEY` must be set.
- `--dry-run` is non-mutating, but still may require auth and network reads.

## Workspace Model

- Default workspace: `~/.ytmusic-organizer`
- Override per run: `--workspace /absolute/path`

All mutable state lives in the workspace (`config.toml`, `state.json`, `managed_playlists.json`, `data/*.json`).

## Commands for Automation

- Setup:
  - `ytmo setup --non-interactive --mode manual --json`
  - `ytmo setup --non-interactive --mode api --json`
  - `ytmo setup --non-interactive --mode manual --dry-run --json`
  - `ytmo setup --non-interactive --mode api --dry-run --json`
- Weekly sync:
  - `ytmo sync --non-interactive --mode manual --json`
  - `ytmo sync --non-interactive --mode api --json`
- Weekly sync dry-run:
  - `ytmo sync --non-interactive --mode manual --dry-run --json`
  - `ytmo sync --non-interactive --mode api --dry-run --json`
- Rebuild (destructive):
  - `ytmo rebuild --yes --non-interactive --mode manual --json`
  - `ytmo rebuild --yes --non-interactive --mode api --json`
- Rebuild dry-run:
  - `ytmo rebuild --non-interactive --mode manual --dry-run --json`
  - `ytmo rebuild --non-interactive --mode api --dry-run --json`
- Cleanup:
  - `ytmo cleanup --yes --local-only --json`
  - `ytmo cleanup --dry-run --json`
  - `ytmo cleanup --local-only --dry-run --json`
- Stats:
  - `ytmo stats --json`
  - `ytmo stats --plan /absolute/path/to/plan.json --json`

Demo note:
- `ytmo demo` is intentionally terminal-only simulation and does not support `--json`.
- Use it for onboarding/live walkthroughs, not machine integration.

## Manual Mode Input Contract

When running `--mode manual`, the command writes a filled prompt file in workspace `data/` and then waits for JSON input.

Example:

```bash
cat plan.json | ytmo sync --mode manual --non-interactive --json
```

## JSON Output Contract

Use `--json` to receive machine-readable output on stdout.

Success shape:

```json
{"status":"ok","command":"sync","result":{"new_likes":3,"missing":1}}
```

Dry-run cleanup success shape:

```json
{"status":"ok","command":"cleanup","result":{"dry_run":true,"would_delete_playlists":2,"would_remove_local_files":6,"skipped_legacy_count":0,"local_only":false}}
```

Error shape:

```json
{"status":"error","command":"setup","error":"Auth file is missing..."}
```

Cancelled shape:

```json
{"status":"cancelled","command":"rebuild","result":{"message":"Cancelled by user"}}
```

Stats success shape:

```json
{"status":"ok","command":"stats","result":{"processed_likes":0,"managed_playlists":0,"missing_matches":0,"plan_diagnostics":{"status":"skipped_missing_plan","plan_path":"/abs/ws/data/playlist_plan.json","liked_path":"/abs/ws/data/liked_songs.json"},"warnings":[]}}
```

Notes:
- `stats` is non-failing for local data issues (missing/invalid artifacts are surfaced through `plan_diagnostics.status` and `warnings`).
- `stats` is read-only and does not rewrite `data/missing_matches.json`.

## Exit Codes

- `0`: command succeeded
- `1`: runtime error or user cancellation
- `2`: CLI argument parsing error
