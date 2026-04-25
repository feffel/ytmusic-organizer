#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PATH="${ROOT_DIR}/.venv/bin:${PATH}"

echo "$ ytmo --help"
ytmo --help
echo
echo "$ ytmo demo --mode manual"
ytmo demo --mode manual
