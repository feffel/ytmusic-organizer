import json
import re
from collections import Counter

def normalize(text: str) -> str:
    text = (text or "").lower().strip()

    text = text.replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")

    # remove common suffix noise
    text = re.sub(r"\b(feat|ft)\.?\b.*", "", text)
    text = re.sub(r"\((.*?)\)", "", text)
    text = re.sub(r"\[(.*?)\]", "", text)
    text = re.sub(r"\b(remaster(ed)?|live|version|official|audio|video|lyrics?)\b", "", text)

    # keep latin, arabic, digits, spaces, hyphens
    text = re.sub(r"[^a-z0-9\u0600-\u06FF\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def title_match(plan_title: str, track_title: str) -> bool:
    pt = normalize(plan_title)
    tt = normalize(track_title)

    if not pt or not tt:
        return False

    if pt == tt:
        return True

    if pt in tt or tt in pt:
        return True

    return False

def artist_match(plan_artist: str, track_artists: list[str]) -> bool:
    pa = normalize(plan_artist)
    tas = [normalize(a) for a in (track_artists or [])]

    if not pa or not tas:
        return False

    if pa in tas:
        return True

    for a in tas:
        if pa in a or a in pa:
            return True

    return False

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

with open("data/liked_songs.json", "r", encoding="utf-8") as f:
    liked_tracks = json.load(f)

with open("data/playlist_plan.json", "r", encoding="utf-8") as f:
    plan = json.load(f)

total_matched = 0
total_missing = 0
total_loose = 0
total_ambiguous = 0

missing_items = []
match_type_counter = Counter()

for playlist in plan.get("playlists", []):
    local_matched = 0
    local_missing = 0
    local_loose = 0
    local_ambiguous = 0

    for song in playlist.get("songs", []):
        match, match_type = find_match(song, liked_tracks)

        if match is None:
            local_missing += 1
            total_missing += 1
            missing_items.append({
                "playlist": playlist.get("name", ""),
                "title": song.get("title", ""),
                "artist": song.get("artist", "")
            })
        else:
            local_matched += 1
            total_matched += 1
            match_type_counter[match_type] += 1

            if match_type == "loose":
                local_loose += 1
                total_loose += 1
            elif match_type == "ambiguous":
                local_ambiguous += 1
                total_ambiguous += 1

    print(f"\n{playlist.get('name', 'Untitled Playlist')}")
    print(
        f"matched: {local_matched}, "
        f"missing: {local_missing}, "
        f"loose: {local_loose}, "
        f"ambiguous: {local_ambiguous}"
    )

print("\nSummary")
print(f"Total matched: {total_matched}")
print(f"Total missing: {total_missing}")
print(f"Total loose: {total_loose}")
print(f"Total ambiguous: {total_ambiguous}")

with open("data/missing_matches.json", "w", encoding="utf-8") as f:
    json.dump(missing_items, f, ensure_ascii=False, indent=2)

print(f"\nWrote data/missing_matches.json with {len(missing_items)} items")
