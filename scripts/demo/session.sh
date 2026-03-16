#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
WORKSPACE="${WORKSPACE:?WORKSPACE is required}"

echo "$ ytmusic-organizer demo session"
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli --help"
"${PYTHON_BIN}" -m ytmusic_organizer.cli --help
echo
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli cleanup --workspace ${WORKSPACE} --local-only --yes --json"
"${PYTHON_BIN}" -m ytmusic_organizer.cli cleanup --workspace "${WORKSPACE}" --local-only --yes --json
echo
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli stats --workspace ${WORKSPACE} --json"
"${PYTHON_BIN}" -m ytmusic_organizer.cli stats --workspace "${WORKSPACE}" --json
