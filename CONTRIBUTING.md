# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
make hooks-install
```

## Test

```bash
make verify
```

## Guidelines

- Keep auth and local workspace files out of git.
- Add tests for behavior changes.
- Keep destructive behavior behind explicit confirmation.
