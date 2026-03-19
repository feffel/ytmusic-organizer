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


def find_match(
    song: dict[str, Any], source_tracks: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str]:
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
        return _pick_best(song, strong), "ambiguous"
    if len(loose) == 1:
        return loose[0], "loose"
    return None, "missing"


def _pick_best(song: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    plan_title = normalize(song.get("title", ""))
    plan_artist = normalize(song.get("artist", ""))

    def sort_key(track: dict[str, Any]) -> tuple[Any, ...]:
        track_title = normalize(track.get("title", ""))
        artists = [normalize(a) for a in (track.get("artists") or [])]
        artist_exact = any(a == plan_artist for a in artists if a)
        return (
            0 if track_title == plan_title else 1,
            0 if artist_exact else 1,
            abs(len(track_title) - len(plan_title)),
            track_title,
            " ".join(artists),
            str(track.get("videoId", "")),
        )

    return sorted(matches, key=sort_key)[0]
