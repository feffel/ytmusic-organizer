import json

with open("data/liked_songs.json", "r", encoding="utf-8") as f:
    liked = json.load(f)

ids = []
for t in liked:
    vid = t.get("videoId")
    if vid:
        ids.append(vid)

with open("state.json", "w", encoding="utf-8") as f:
    json.dump({"processed_video_ids": ids}, f, ensure_ascii=False, indent=2)

print(f"Initialized state with {len(ids)} songs")
