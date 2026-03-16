#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python}"
WORKSPACE="${WORKSPACE:?WORKSPACE is required}"

echo "$ ytmusic-organizer demo session"
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli --help"
"${PYTHON_BIN}" -m ytmusic_organizer.cli --help
echo
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli demo --workspace ${WORKSPACE} --mode manual"
"${PYTHON_BIN}" -m ytmusic_organizer.cli demo --workspace "${WORKSPACE}" --mode manual
echo
echo "$ ${PYTHON_BIN} -m ytmusic_organizer.cli demo --workspace ${WORKSPACE} --mode api"
"${PYTHON_BIN}" -m ytmusic_organizer.cli demo --workspace "${WORKSPACE}" --mode api
