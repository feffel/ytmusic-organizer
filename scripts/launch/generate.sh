#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STAMP="$(date +%Y-%m-%d-%H%M%S)"
OUT_DIR="${ROOT_DIR}/artifacts/launch/${STAMP}"
mkdir -p "${OUT_DIR}"
STATS_WORKSPACE="${STATS_WORKSPACE:-/tmp/ytmo-launch-stats}"

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "${ROOT_DIR}/pyproject.toml" | head -n 1)"
if [ -z "${VERSION}" ]; then
  echo "Could not determine version from pyproject.toml"
  exit 1
fi

RELEASE_URL="https://github.com/feffel/ytmusic-organizer/releases/tag/v${VERSION}"
REPO_URL="https://github.com/feffel/ytmusic-organizer"

if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PYTHON_BIN="python"
fi

STATS_JSON="${OUT_DIR}/stats.json"
"${PYTHON_BIN}" -m ytmusic_organizer.cli stats --workspace "${STATS_WORKSPACE}" --json > "${STATS_JSON}"

cp "${ROOT_DIR}/CHANGELOG.md" "${OUT_DIR}/CHANGELOG.md"

cat > "${OUT_DIR}/project-metadata.json" <<EOF
{
  "project_id": "ytmusic-organizer",
  "name": "ytmusic-organizer",
  "tagline": "Playlist automation, human taste.",
  "repo_url": "${REPO_URL}",
  "install_command": "pipx install ytmusic-organizer",
  "release_url": "${RELEASE_URL}",
  "release_version": "${VERSION}",
  "generated_at": "${STAMP}"
}
EOF

cat > "${OUT_DIR}/README.md" <<EOF
# Launch Input Bundle

Generated: ${STAMP}

Files:
- project metadata: project-metadata.json
- release notes source: CHANGELOG.md
- optional metrics: stats.json

Suggested private-orchestrator command:
\`\`\`bash
cd /Users/felfel/dev/felfel-studio
python scripts/launch_automation/generate.py ytmusic-organizer \\
  --stats-json "${OUT_DIR}/stats.json" \\
  --release-notes "${OUT_DIR}/CHANGELOG.md"
\`\`\`
EOF

echo "Launch input bundle created: ${OUT_DIR}"
