#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/demo"

mkdir -p "${OUT_DIR}"

SENSITIVE_PATTERNS='OPENAI_API_KEY|browser\.json|SAPISID|Authorization:|Cookie:|oauth|access_token|refresh_token'
TEXT_FILES="$(find "${OUT_DIR}" -type f \( -name '*.cast' -o -name '*.log' -o -name '*.txt' \) 2>/dev/null || true)"

if [ -n "${TEXT_FILES}" ]; then
  if grep -R -E -n "${SENSITIVE_PATTERNS}" ${TEXT_FILES}; then
    echo "Sensitive content detected in demo artifacts."
    exit 1
  fi
fi

echo "Demo artifact validation passed."
