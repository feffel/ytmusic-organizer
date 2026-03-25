#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/demo"
GIF_FILE="${OUT_DIR}/demo.gif"
MP4_FILE="${OUT_DIR}/demo.mp4"
README_GIF_FILE="${ROOT_DIR}/docs/assets/demo.gif"

if ! command -v vhs >/dev/null 2>&1; then
  echo "vhs is required. Install: https://github.com/charmbracelet/vhs"
  exit 1
fi

mkdir -p "${OUT_DIR}"
mkdir -p "$(dirname "${README_GIF_FILE}")"

TAPE_FILE="${OUT_DIR}/demo.tape"
cat > "${TAPE_FILE}" <<EOF
Output artifacts/demo/demo.gif
Set FontSize 16
Set FontFamily "Menlo"
Set Width 1200
Set Height 700
Set Framerate 30
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms
Env PATH "${ROOT_DIR}/.venv/bin:${PATH}"

Type "ytmo --help"
Enter
Sleep 1s

Type "ytmo demo --mode manual"
Enter
Sleep 12s
EOF

cd "${ROOT_DIR}"
vhs "${TAPE_FILE}"

if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -y -i "${GIF_FILE}" "${MP4_FILE}" >/dev/null 2>&1
  echo "Rendered demo mp4: ${MP4_FILE}"
else
  echo "ffmpeg not found; skipped mp4 rendering."
fi

cp "${GIF_FILE}" "${README_GIF_FILE}"
./scripts/demo/validate.sh
echo "Rendered demo gif: ${GIF_FILE}"
echo "Refreshed README demo gif: ${README_GIF_FILE}"
