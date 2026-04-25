# Demo Recording Guide

This repository commits demo scripts and one curated README demo asset.

Policy:
- Generated demo outputs must stay under `artifacts/demo/`.
- Do not commit `.cast`, `.gif`, or `.mp4` files except for `docs/assets/demo.gif`.
- CI and `make demo-check` fail if media binaries outside that exception are tracked.

## Prerequisites

- `asciinema` for optional cast recording
- `vhs` for rendering the README GIF from the scripted demo session
- optional: `ffmpeg` for MP4 conversion

## Commands

The demo session script uses `ytmo demo` (manual + api simulation modes) as the primary walkthrough source.

Record a raw cast for review/debugging:

```bash
make demo-record
```

Render the demo GIF (and MP4 when ffmpeg is available):

```bash
make demo-render
```

`make demo-render` now does three things:
- runs the scripted demo session through `vhs`
- writes ignored outputs under `artifacts/demo/`
- refreshes the tracked README asset at `docs/assets/demo.gif`

Enforce no tracked media:

```bash
make demo-check
```

## README Demo Asset Flow

1. Run `make demo-render`.
2. Review `artifacts/demo/demo.gif` and the embedded preview in `README.md`.
3. Commit the refreshed `docs/assets/demo.gif` when the README demo changes.
4. Run `make demo-check` before commit to ensure no other media binaries are tracked.
