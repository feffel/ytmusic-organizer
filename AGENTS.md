# AGENTS.md

## Scope
These instructions apply to this repository.

## Operating Rules
- Be pragmatic and concise.
- Challenge questionable decisions with concrete technical reasoning.
- Ask clarifying questions when assumptions would be risky.
- Explain tradeoffs before presenting options.
- Avoid filler language.

## Canonical Project Memory
- `CODEX_CONTEXT.md` is the canonical high-level project context.
- When changes affect workflows, scripts/modules, data flow, commands, file structure, or dependencies, update `CODEX_CONTEXT.md` in the same change.
- Do not remove historical context unless it is no longer accurate.

## Workflow Conventions
- Prefer CLI entrypoints over ad-hoc scripts:
  - `ytmo setup`
  - `ytmo sync`
  - `ytmo reset`
  - `ytmo cleanup`
  - `ytmo stats`
- Make targets must reflect actual supported CLI behavior.

## State and Safety Conventions
- Treat `~/.ytmusic-organizer/` as the active mutable workspace by default.
- Do not overwrite or expose `browser.json`.
- Only delete playlists listed in `managed_playlists.json`.
- Never perform arbitrary playlist deletion.
- `state.json` should grow during normal sync; full reset may reinitialize it.

## Data Artifact Conventions
- Generated workspace artifacts include:
  - `data/liked_songs.json`
  - `data/new_likes.json`
  - `data/playlist_plan.json`
  - `data/new_plan.json`
  - `data/missing_matches.json`
  - `state.json`
  - `managed_playlists.json`
- Keep generated artifacts out of source control unless explicitly required.

## Verification
- Before claiming completion on behavior changes, run relevant tests (`make test` or targeted unit tests).
- If tests are skipped, state that explicitly.
