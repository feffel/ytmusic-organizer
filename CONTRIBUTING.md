# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Guidelines

- Keep auth and local workspace files out of git.
- Add tests for behavior changes.
- Keep destructive behavior behind explicit confirmation.
