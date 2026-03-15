import re
from typing import Any


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


def find_match(song: dict[str, Any], source_tracks: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    plan_title = song.get("title", "")
    plan_artist = song.get("artist", "")

    strong: list[dict[str, Any]] = []
    loose: list[dict[str, Any]] = []

    for track in source_tracks:
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
