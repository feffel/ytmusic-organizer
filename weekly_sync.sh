#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

rm -f data/new_plan.json
rm -f data/missing_matches.json

if [ ! -d ".venv" ]; then
  echo "Error: .venv not found in $PROJECT_DIR"
  exit 1
fi

source .venv/bin/activate

echo
echo "== Step 1: Export newly liked songs =="
python scripts/export_new_likes.py

if [ ! -f "data/new_likes.json" ]; then
  echo "Error: data/new_likes.json was not created"
  exit 1
fi

NEW_COUNT=$(python - <<'PY'
import json
try:
    with open("data/new_likes.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(len(data))
except Exception:
    print(-1)
PY
)

if [ "$NEW_COUNT" = "-1" ]; then
  echo "Error: could not read data/new_likes.json"
  exit 1
fi

if [ "$NEW_COUNT" = "0" ]; then
  echo
  echo "No new liked songs found. Nothing to do."
  exit 0
fi

echo
echo "Found $NEW_COUNT new liked songs."
echo
echo "== Step 2: Classification pause =="
echo "Open these files:"
echo "  - prompts/gpt_prompt_new_songs.txt"
echo "  - data/new_likes.json"
echo
echo "Then in ChatGPT:"
echo "  1. Copy the prompt from prompts/gpt_prompt_new_songs.txt"
echo "  2. Replace [PASTE CONTENTS OF new_likes.json HERE] with the contents of data/new_likes.json"
echo "  3. Save the JSON response as data/new_plan.json"
echo
echo "This script will wait until data/new_plan.json exists and is valid JSON."

while true; do
  if [ -f "data/new_plan.json" ]; then
    VALID=$(python - <<'PY'
import json
try:
    with open("data/new_plan.json", "r", encoding="utf-8") as f:
        json.load(f)
    print("yes")
except Exception:
    print("no")
PY
)
    if [ "$VALID" = "yes" ]; then
      break
    else
      echo "Found data/new_plan.json but it is not valid JSON yet. Waiting..."
    fi
  fi
  sleep 3
done

echo
echo "== Step 3: Apply new playlist assignments =="
python scripts/apply_new_likes.py

echo
echo "== Sync complete =="
echo "Files updated:"
echo "  - state.json"
echo "  - data/missing_matches.json"
