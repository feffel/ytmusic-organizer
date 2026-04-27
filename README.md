# ytmusic-organizer

[![PyPI](https://img.shields.io/pypi/v/ytmusic-organizer?label=PyPI&color=0A7BBB)](https://pypi.org/project/ytmusic-organizer/)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://pypi.org/project/ytmusic-organizer/)
[![License](https://img.shields.io/pypi/l/ytmusic-organizer?color=6aa84f)](https://github.com/feffel/ytmusic-organizer/blob/main/LICENSE)
[![CI](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/feffel/ytmusic-organizer/actions/workflows/ci.yml)

your likes are not a playlist system. they are a pile.

`ytmusic-organizer` turns that pile into reusable youtube music playlists with a guided setup and a weekly sync that handles the boring part.

```text
            ██╗   ██╗████████╗███╗   ███╗ ██████╗
            ╚██╗ ██╔╝╚══██╔══╝████╗ ████║██╔═══██╗
             ╚████╔╝    ██║   ██╔████╔██║██║   ██║
              ╚██╔╝     ██║   ██║╚██╔╝██║██║   ██║
               ██║      ██║   ██║ ╚═╝ ██║╚██████╔╝
               ╚═╝      ╚═╝   ╚═╝     ╚═╝ ╚═════╝

            Y T M O  •  playlist automation, human taste.
```

## demo

![ytmusic-organizer demo](docs/assets/demo.gif)

## good fit

- you dump tracks into youtube music likes and want usable playlists out of it.
- you want a weekly sync instead of another manual cleanup ritual.
- you prefer a cli that does the job over hand-curating playlists every week.

## what it does

- builds an initial playlist structure from your liked songs.
- applies weekly incremental updates as you like new tracks.
- supports `manual` mode when you want to provide JSON plans and `api` mode when you want openai-backed planning.
- keeps state in `~/.ytmusic-organizer` by default so runs stay repeatable.

## install

recommended:

```bash
pipx install ytmusic-organizer
```

from source:

```bash
pipx install .
```

## first run

1. run guided setup:

```bash
ytmo setup
```

By default, setup opens a YouTube Music browser window and captures the required
auth headers after you log in. If browser capture is unavailable, setup falls
back to manual header paste. If Playwright reports that Chromium is missing,
run:

```bash
python -m playwright install chromium
```

2. run your weekly sync:

```bash
ytmo sync
```

3. if you want end-to-end planning, use api mode:

```bash
export OPENAI_API_KEY=...
ytmo sync --mode api
```

## safety model

- deletes only playlists listed in `managed_playlists.json`, using playlist ids.
- never performs arbitrary playlist deletion.
- `rebuild` and `cleanup` are destructive and require explicit confirmation unless `--yes` is passed.
- `--dry-run` does not write playlists or workspace artifacts, but it may still require auth and network reads.

## core commands

- `ytmo setup` - guided bootstrap and initial playlist build
- `ytmo sync` - weekly incremental updates
- `ytmo rebuild --yes` - full destructive rebuild
- `ytmo cleanup --yes` - remove managed playlists and local managed artifacts
- `ytmo stats` - read-only workspace diagnostics
- `ytmo demo` - simulation walkthrough with no auth, network, or writes

## docs

- cli and reference details: [docs/reference.md](docs/reference.md)
- automation integration: [docs/automation.md](docs/automation.md)
- demo asset workflow: [docs/demo.md](docs/demo.md)
- collaborator workflows: [docs/collaborators.md](docs/collaborators.md)
