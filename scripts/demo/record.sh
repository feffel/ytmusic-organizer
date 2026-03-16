#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/demo"
CAST_FILE="${OUT_DIR}/demo.cast"
LOG_FILE="${OUT_DIR}/demo.log"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "asciinema is required. Install: https://asciinema.org/docs/installation"
  exit 1
fi

mkdir -p "${OUT_DIR}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

WORKSPACE="${TMP_DIR}/workspace"
mkdir -p "${WORKSPACE}"

if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python"
fi

cd "${ROOT_DIR}"
ASCIINEMA_REC=1 \
  PYTHON_BIN="${PYTHON_BIN}" \
  WORKSPACE="${WORKSPACE}" \
  asciinema rec --overwrite --idle-time-limit 1 --command "./scripts/demo/session.sh" "${CAST_FILE}" | tee "${LOG_FILE}"

./scripts/demo/validate.sh
echo "Recorded demo cast: ${CAST_FILE}"
