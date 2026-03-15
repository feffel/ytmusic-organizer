import functools
import json
import requests
from ytmusicapi import YTMusic

s = requests.Session()
s.request = functools.partial(s.request, timeout=90)

yt = YTMusic("browser.json", requests_session=s)

songs = yt.get_liked_songs(limit=5000)

tracks = []
for t in songs.get("tracks", []):
    tracks.append({
        "videoId": t.get("videoId"),
        "title": t.get("title", ""),
        "artists": [a.get("name", "") for a in t.get("artists", [])],
        "album": (t.get("album") or {}).get("name", ""),
        "duration": t.get("duration", ""),
    })

with open("data/liked_songs.json", "w", encoding="utf-8") as f:
    json.dump(tracks, f, ensure_ascii=False, indent=2)

print(f"Exported {len(tracks)} songs to data/liked_songs.json")
