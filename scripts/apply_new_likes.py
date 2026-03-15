import json
import re
import functools
import requests
from ytmusicapi import YTMusic

def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = text.replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\b(feat|ft)\.?\b.*", "", text)
    text = re.sub(r"\((.*?)\)", "", text)
    text = re.sub(r"\[(.*?)\]", "", text)
    text = re.sub(r"\b(remaster(ed)?|live|version|official|audio|video|lyrics?)\b", "", text)
    text = re.sub(r"[^a-z0-9\u0600-\u06FF\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def title_match(plan_title: str, track_title: str) -> bool:
    pt = normalize(plan_title)
    tt = normalize(track_title)
    if not pt or not tt:
        return False
    return pt == tt or pt in tt or tt in pt

def artist_match(plan_artist: str, track_artists: list[str]) -> bool:
    pa = normalize(plan_artist)
    tas = [normalize(a) for a in (track_artists or [])]
    if not pa or not tas:
        return False
    if pa in tas:
        return True
    return any(pa in a or a in pa for a in tas)

def find_match(song: dict, source_tracks: list[dict]):
    plan_title = song.get("title", "")
    plan_artist = song.get("artist", "")

    strong = []
    loose = []

    for track in source_tracks:
        if title_match(plan_title, track.get("title", "")):
            if artist_match(plan_artist, track.get("artists", [])):
                strong.append(track)
            else:
                loose.append(track)

    if len(strong) >= 1:
        return strong[0], "exact-or-ambiguous"

    if len(loose) == 1:
        return loose[0], "loose"

    return None, "missing"

def build_existing_playlist_map(yt: YTMusic):
    playlists = yt.get_library_playlists(limit=500)
    playlist_map = {}
    for p in playlists:
        name = (p.get("title") or "").strip()
        playlist_id = p.get("playlistId")
        if name and playlist_id:
            playlist_map[normalize(name)] = {
                "title": name,
                "playlistId": playlist_id
            }
    return playlist_map

def get_existing_video_ids_in_playlist(yt: YTMusic, playlist_id: str):
    try:
        playlist_data = yt.get_playlist(playlist_id, limit=5000)
        ids = set()
        for track in playlist_data.get("tracks", []):
            video_id = track.get("videoId")
            if video_id:
                ids.add(video_id)
        return ids
    except Exception as e:
        print(f"Warning: could not read playlist contents for {playlist_id}: {e}")
        return set()

session = requests.Session()
session.request = functools.partial(session.request, timeout=90)
yt = YTMusic("browser.json", requests_session=session)

with open("data/new_likes.json", "r", encoding="utf-8") as f:
    new_likes = json.load(f)

with open("data/new_plan.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
except FileNotFoundError:
    state = {"processed_video_ids": []}

processed = set(state.get("processed_video_ids", []))
playlist_map = build_existing_playlist_map(yt)

missing = []
matched_video_ids = set()
results = []

for playlist in plan.get("playlists", []):
    name = (playlist.get("name") or "").strip()
    if not name:
        print("Skipping empty playlist name")
        continue

    normalized_name = normalize(name)
    playlist_info = playlist_map.get(normalized_name)

    if not playlist_info:
        print(f"Missing destination playlist: {name}")
        results.append({"name": name, "added": 0, "status": "missing-playlist"})
        continue

    playlist_id = playlist_info["playlistId"]
    existing_ids = get_existing_video_ids_in_playlist(yt, playlist_id)
    to_add = []
    seen_for_this_playlist = set()

    for song in playlist.get("songs", []):
        match, match_type = find_match(song, new_likes)

        if not match:
            missing.append({
                "playlist": name,
                "title": song.get("title", ""),
                "artist": song.get("artist", "")
            })
            continue

        video_id = match.get("videoId")
        if not video_id:
            missing.append({
                "playlist": name,
                "title": song.get("title", ""),
                "artist": song.get("artist", "")
            })
            continue

        matched_video_ids.add(video_id)

        if video_id in seen_for_this_playlist:
            continue

        if video_id in existing_ids:
            continue

        seen_for_this_playlist.add(video_id)
        to_add.append(video_id)

    if to_add:
        yt.add_playlist_items(playlist_id, to_add)

    results.append({
        "name": name,
        "added": len(to_add),
        "status": "ok"
    })

    print(f"{name}: added {len(to_add)} songs")

processed.update(matched_video_ids)

with open("state.json", "w", encoding="utf-8") as f:
    json.dump({"processed_video_ids": sorted(processed)}, f, ensure_ascii=False, indent=2)

with open("data/missing_matches.json", "w", encoding="utf-8") as f:
    json.dump(missing, f, ensure_ascii=False, indent=2)

print("\nDone.\n")
print("Results:")
for item in results:
    print(f"- {item['name']}: {item['added']} added ({item['status']})")

print(f"\nProcessed unique songs this run: {len(matched_video_ids)}")
print(f"Missing matches: {len(missing)}")
print("Updated state.json")
