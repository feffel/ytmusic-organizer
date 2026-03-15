#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  echo "Error: .venv not found in $PROJECT_DIR"
  exit 1
fi

source .venv/bin/activate

rm -f data/playlist_plan.json
rm -f data/missing_matches.json

echo
echo "== Step 1: Export full liked songs =="
python scripts/export_liked.py

if [ ! -f "data/liked_songs.json" ]; then
  echo "Error: data/liked_songs.json was not created"
  exit 1
fi

TOTAL_COUNT=$(python - <<'PY'
import json
try:
    with open("data/liked_songs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(len(data))
except Exception:
    print(-1)
PY
)

if [ "$TOTAL_COUNT" = "-1" ]; then
  echo "Error: could not read data/liked_songs.json"
  exit 1
fi

echo
echo "Exported $TOTAL_COUNT liked songs."
echo
echo "== Step 2: Fresh classification pause =="
echo "Open these files:"
echo "  - prompts/gpt_prompt_full_reset.txt"
echo "  - data/liked_songs.json"
echo
echo "Then in ChatGPT:"
echo "  1. Copy the prompt from prompts/gpt_prompt_full_reset.txt"
echo "  2. Replace [PASTE CONTENTS OF liked_songs.json HERE] with the contents of data/liked_songs.json"
echo "  3. Save the JSON response as data/playlist_plan.json"
echo
echo "This script will wait until data/playlist_plan.json exists and is valid JSON."

while true; do
  if [ -f "data/playlist_plan.json" ]; then
    VALID=$(python - <<'PY'
import json
try:
    with open("data/playlist_plan.json", "r", encoding="utf-8") as f:
        json.load(f)
    print("yes")
except Exception:
    print("no")
PY
)
    if [ "$VALID" = "yes" ]; then
      break
    else
      echo "Found data/playlist_plan.json but it is not valid JSON yet. Waiting..."
    fi
  fi
  sleep 3
done

echo
echo "== Step 3: Update managed playlist list =="
python scripts/update_managed_playlists.py

echo
echo "== Step 4: Delete old managed playlists =="
python scripts/delete_managed_playlists.py

echo
echo "== Step 5: Recreate playlists from fresh plan =="
python scripts/apply_plan.py

echo
echo "== Step 6: Reset incremental state =="
python scripts/initialize_state.py

echo
echo "== Full reset complete =="
echo "Files updated:"
echo "  - data/playlist_plan.json"
echo "  - managed_playlists.json"
echo "  - state.json"
echo "  - data/missing_matches.json"
