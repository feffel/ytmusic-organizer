import json
import functools
import requests
from ytmusicapi import YTMusic

session = requests.Session()
session.request = functools.partial(session.request, timeout=90)

yt = YTMusic("browser.json", requests_session=session)

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
except FileNotFoundError:
    state = {"processed_video_ids": []}

processed = set(state.get("processed_video_ids", []))

songs = yt.get_liked_songs(limit=5000)
tracks = []

for t in songs.get("tracks", []):
    video_id = t.get("videoId")
    if not video_id or video_id in processed:
        continue

    tracks.append({
        "videoId": video_id,
        "title": t.get("title", ""),
        "artists": [a.get("name", "") for a in t.get("artists", [])],
        "album": (t.get("album") or {}).get("name", ""),
        "duration": t.get("duration", "")
    })

with open("data/new_likes.json", "w", encoding="utf-8") as f:
    json.dump(tracks, f, ensure_ascii=False, indent=2)

print(f"Found {len(tracks)} new liked songs")
