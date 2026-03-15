import json

with open("data/playlist_plan.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

names = []
seen = set()

for p in plan.get("playlists", []):
    name = (p.get("name") or "").strip()
    if not name:
        continue
    key = name.lower()
    if key in seen:
        continue
    seen.add(key)
    names.append(name)

with open("managed_playlists.json", "w", encoding="utf-8") as f:
    json.dump({"playlists": names}, f, ensure_ascii=False, indent=2)

print(f"Wrote managed_playlists.json with {len(names)} playlists")
