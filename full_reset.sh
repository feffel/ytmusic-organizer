#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo "Error: .venv not found in $PROJECT_DIR"
  exit 1
fi

source .venv/bin/activate

python -m ytmusic_organizer.cli reset --workspace .ytmo "$@"
