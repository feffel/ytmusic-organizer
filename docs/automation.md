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

## Workspace Model

- Default workspace: `~/.ytmusic-organizer`
- Override per run: `--workspace /absolute/path`

All mutable state lives in the workspace (`config.toml`, `state.json`, `managed_playlists.json`, `data/*.json`).

## Commands for Automation

- Setup:
  - `ytmo setup --non-interactive --plan-from-stdin --mode manual --json`
  - `ytmo setup --non-interactive --mode api --json`
- Weekly sync:
  - `ytmo sync --non-interactive --plan-from-stdin --mode manual --json`
  - `ytmo sync --non-interactive --mode api --json`
- Full reset (destructive):
  - `ytmo reset --yes --non-interactive --plan-from-stdin --mode manual --json`
  - `ytmo reset --yes --non-interactive --mode api --json`
- Cleanup:
  - `ytmo cleanup --yes --local-only --json`

## Manual Mode Input Contract

When running `--mode manual`, the command writes a filled prompt file in workspace `data/` and then waits for JSON on stdin.

Example:

```bash
cat plan.json | ytmo sync --mode manual --non-interactive --plan-from-stdin --json
```

## JSON Output Contract

Use `--json` to receive machine-readable output on stdout.

Success shape:

```json
{"status":"ok","command":"sync","result":{"new_likes":3,"missing":1}}
```

Error shape:

```json
{"status":"error","command":"setup","error":"Auth file is missing..."}
```

Cancelled shape:

```json
{"status":"cancelled","command":"reset","result":{"message":"Cancelled by user"}}
```

## Exit Codes

- `0`: command succeeded
- `1`: runtime error or user cancellation
- `2`: CLI argument parsing error
