# ytmusic-organizer

[![PyPI](https://img.shields.io/pypi/v/ytmusic-organizer?label=PyPI&color=0A7BBB)](https://pypi.org/project/ytmusic-organizer/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/ytmusic-organizer/)
[![License](https://img.shields.io/pypi/l/ytmusic-organizer?color=6aa84f)](https://github.com/feffel/ytmusic-organizer/blob/main/LICENSE)
[![CI](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml)

Organize YouTube Music likes into practical playlists with a guided setup and fast weekly sync.

```text
            ██╗   ██╗████████╗███╗   ███╗ ██████╗
            ╚██╗ ██╔╝╚══██╔══╝████╗ ████║██╔═══██╗
             ╚████╔╝    ██║   ██╔████╔██║██║   ██║
              ╚██╔╝     ██║   ██║╚██╔╝██║██║   ██║
               ██║      ██║   ██║ ╚═╝ ██║╚██████╔╝
               ╚═╝      ╚═╝   ╚═╝     ╚═╝ ╚═════╝

            Y T M O  •  Playlist Automation, Human Taste.
```

## Demo

- Demo GIF: `https://github.com/feffel/ytmusic-organizer/releases/latest`

## Good Fit

- You like songs in YouTube Music and want reusable playlists quickly.
- You want a repeatable weekly sync workflow.
- You prefer a CLI workflow over manual playlist curation.

## What It Does

- Builds an initial playlist structure from your liked songs.
- Applies weekly incremental updates as you like new songs.
- Supports `manual` mode (you provide JSON plans) and `api` mode (OpenAI-backed planning).
- Uses a workspace (`~/.ytmusic-organizer` by default) so runs are repeatable.

## Install

Recommended:

```bash
pipx install ytmusic-organizer
```

From source:

```bash
pipx install .
```

## First Run (2 Minutes)

1. Run guided setup:

```bash
ytmo setup
```

2. For weekly updates:

```bash
ytmo sync
```

3. Optional: API mode for faster end-to-end planning:

```bash
export OPENAI_API_KEY=...
ytmo sync --mode api
```

## Safety Model

- Deletes only playlists listed in `managed_playlists.json` (ID-based targeting).
- Never performs arbitrary playlist deletion.
- `rebuild` and `cleanup` are destructive and require explicit confirmation unless `--yes` is passed.
- `--dry-run` is non-mutating (no remote playlist writes and no workspace artifact writes), but may still require auth and network reads.

## Core Commands

- `ytmo setup` - guided bootstrap and initial playlist build
- `ytmo sync` - weekly incremental updates
- `ytmo rebuild --yes` - full destructive rebuild
- `ytmo cleanup --yes` - remove managed playlists and local managed artifacts
- `ytmo stats` - read-only workspace diagnostics
- `ytmo demo` - simulation walkthrough (no auth/network/write)

## Docs

- CLI/reference details: [docs/reference.md](docs/reference.md)
- Automation integration: [docs/automation.md](docs/automation.md)
- Collaborator workflows: [docs/collaborators.md](docs/collaborators.md)
