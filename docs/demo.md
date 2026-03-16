# Demo Recording Guide

This repository commits demo scripts, not generated media.

Policy:
- Generated demo outputs must stay under `artifacts/demo/`.
- Do not commit `.cast`, `.gif`, or `.mp4` files.
- CI and `make demo-check` fail if media binaries are tracked.

## Prerequisites

- `asciinema` for terminal recording
- `vhs` for rendering GIF from cast
- optional: `ffmpeg` for MP4 conversion

## Commands

Record cast + validate output:

```bash
make demo-record
```

Render GIF (and MP4 when ffmpeg is available):

```bash
make demo-render
```

Enforce no tracked media:

```bash
make demo-check
```

## README Demo Asset Flow

1. Tag and publish release as normal (`vX.Y.Z`).
2. Upload `artifacts/demo/demo.gif` (and optional `demo.mp4`) to that GitHub Release.
3. Update README demo URL to point at the release asset URL.
4. Run `make demo-check` before commit to ensure binaries are not tracked.
