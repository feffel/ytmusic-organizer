import json
import functools
import requests
from ytmusicapi import YTMusic

def normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())

session = requests.Session()
session.request = functools.partial(session.request, timeout=90)
yt = YTMusic("browser.json", requests_session=session)

with open("managed_playlists.json", "r", encoding="utf-8") as f:
    managed = json.load(f)

managed_names = {normalize(name) for name in managed.get("playlists", [])}

library_playlists = yt.get_library_playlists(limit=500)

deleted = []
kept = []

for p in library_playlists:
    title = (p.get("title") or "").strip()
    playlist_id = p.get("playlistId")

    if not title or not playlist_id:
        continue

    if normalize(title) in managed_names:
        print(f"Deleting managed playlist: {title}")
        yt.delete_playlist(playlist_id)
        deleted.append(title)
    else:
        kept.append(title)

print("\nDone.")
print(f"Deleted {len(deleted)} managed playlists.")
