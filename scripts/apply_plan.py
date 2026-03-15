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

def find_match(song: dict, liked_tracks: list[dict]):
    plan_title = song.get("title", "")
    plan_artist = song.get("artist", "")

    strong = []
    loose = []

    for track in liked_tracks:
        if title_match(plan_title, track.get("title", "")):
            if artist_match(plan_artist, track.get("artists", [])):
                strong.append(track)
            else:
                loose.append(track)

    if len(strong) == 1:
        return strong[0], "exact"

    if len(strong) > 1:
        return strong[0], "ambiguous"

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
        existing_ids = set()

        for track in playlist_data.get("tracks", []):
            video_id = track.get("videoId")
            if video_id:
                existing_ids.add(video_id)

        return existing_ids
    except Exception as e:
        print(f"Warning: could not read playlist contents for {playlist_id}: {e}")
        print("Continuing as if the playlist is empty.")
        return set()

# session with longer timeout
session = requests.Session()
session.request = functools.partial(session.request, timeout=90)

yt = YTMusic("browser.json", requests_session=session)

with open("data/liked_songs.json", "r", encoding="utf-8") as f:
    liked_tracks = json.load(f)

with open("data/playlist_plan.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

existing_playlists = build_existing_playlist_map(yt)

results = []
missing_items = []

for playlist in plan.get("playlists", []):
    playlist_name = (playlist.get("name") or "").strip()
    if not playlist_name:
        print("Skipping playlist with empty name")
        continue

    normalized_name = normalize(playlist_name)

    if normalized_name in existing_playlists:
        playlist_id = existing_playlists[normalized_name]["playlistId"]
        action = "reused"
        print(f"Reusing existing playlist: {playlist_name}")
        existing_video_ids = get_existing_video_ids_in_playlist(yt, playlist_id)
    else:
        playlist_id = yt.create_playlist(
            title=playlist_name,
            description="Created from liked songs organizer"
        )
        existing_playlists[normalized_name] = {
            "title": playlist_name,
            "playlistId": playlist_id
        }
        action = "created"
        print(f"Created new playlist: {playlist_name}")
        # Important: newly created playlist may fail to parse when fetched immediately
        existing_video_ids = set()

    video_ids_to_add = []
    seen_video_ids = set()

    for song in playlist.get("songs", []):
        match, match_type = find_match(song, liked_tracks)

        if match is None:
            missing_items.append({
                "playlist": playlist_name,
                "title": song.get("title", ""),
                "artist": song.get("artist", "")
            })
            continue

        video_id = match.get("videoId")
        if not video_id:
            missing_items.append({
                "playlist": playlist_name,
                "title": song.get("title", ""),
                "artist": song.get("artist", "")
            })
            continue

        if video_id in seen_video_ids:
            continue

        if video_id in existing_video_ids:
            continue

        seen_video_ids.add(video_id)
        video_ids_to_add.append(video_id)

    if video_ids_to_add:
        yt.add_playlist_items(playlist_id, video_ids_to_add)

    results.append({
        "name": playlist_name,
        "action": action,
        "added_count": len(video_ids_to_add),
        "already_present_count": len(existing_video_ids),
    })

    print(
        f"Playlist '{playlist_name}': "
        f"added {len(video_ids_to_add)} songs, "
        f"already had {len(existing_video_ids)}"
    )

with open("data/missing_matches.json", "w", encoding="utf-8") as f:
    json.dump(missing_items, f, ensure_ascii=False, indent=2)

print("\nDone.\n")
print("Playlist results:")
for p in results:
    print(
        f"- {p['name']} ({p['action']}): "
        f"added {p['added_count']}, already had {p['already_present_count']}"
    )

print(f"\nWrote data/missing_matches.json with {len(missing_items)} items")
