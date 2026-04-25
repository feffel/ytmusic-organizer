# Changelog

## [0.2.1] - 2026-04-25

### Changed

- Bump the app and package version to `0.2.1`.
- Report stats coverage as processed likes divided by the total liked snapshot size.

### Fixed

- Count artists across each full playlist when deriving stats podium labels, while keeping sample songs capped at three.

## [0.2.0] - 2026-03-25

### Added

- safe `--dry-run` support across setup, sync, rebuild, and cleanup
- `ytmo demo` for terminal-only setup walkthrough simulation
- non-failing stats diagnostics with richer local workspace reporting
- maintainer demo tooling for recording, rendering, validating, and embedding the CLI demo
- pre-push verification hooks and dependency review workflow support

### Changed

- replaced the old reset flow with `ytmo rebuild`
- hardened first-run auth, setup resume, and manual classification guidance
- improved interactive stdin handling for browser headers and pasted JSON plans
- refined CLI theming, interruption UX, and scoped subcommand parse help
- split documentation into focused reference, automation, collaborator, and demo guides
- embedded the current demo directly in the README and simplified the recorded command surface
- tightened CI and release gates around verification and successful CI prerequisites

### Fixed

- reliability issues around malformed state, playlist lookups, and large library fetches
- misleading setup completion states when auth is missing or interrupted
- preview and stats flows so diagnostics stay informative instead of failing early

## [0.1.0] - 2026-03-15

### Added

- Installable `ytmo` CLI package (`ytmusic_organizer`)
- Guided `init --bootstrap` onboarding
- Non-destructive bootstrap flow
- Weekly sync and destructive full reset commands
- Plan validation, config handling, and bootstrap precondition checks
- Unit and CLI smoke tests
- Open-source project metadata and CI
