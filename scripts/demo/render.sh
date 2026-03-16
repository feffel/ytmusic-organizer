#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/demo"
CAST_FILE="${OUT_DIR}/demo.cast"
GIF_FILE="${OUT_DIR}/demo.gif"
MP4_FILE="${OUT_DIR}/demo.mp4"

if [ ! -f "${CAST_FILE}" ]; then
  echo "Missing cast file: ${CAST_FILE}. Run ./scripts/demo/record.sh first."
  exit 1
fi

if ! command -v vhs >/dev/null 2>&1; then
  echo "vhs is required. Install: https://github.com/charmbracelet/vhs"
  exit 1
fi

mkdir -p "${OUT_DIR}"
TAPE_FILE="${OUT_DIR}/demo.tape"
cat > "${TAPE_FILE}" <<EOF
Output ${GIF_FILE}
Set FontSize 16
Set Width 1200
Set Height 700
Set Theme "Catppuccin Mocha"
Play ${CAST_FILE}
EOF

vhs "${TAPE_FILE}"

if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -i "${GIF_FILE}" "${MP4_FILE}" >/dev/null 2>&1
  echo "Rendered demo mp4: ${MP4_FILE}"
else
  echo "ffmpeg not found; skipped mp4 rendering."
fi

./scripts/demo/validate.sh
echo "Rendered demo gif: ${GIF_FILE}"
