from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import requests
from ytmusicapi import YTMusic

from .matching import find_match, normalize


def build_playlist_description(playlist: dict[str, Any]) -> str:
    managed_tag = "Managed by ytmusic-organizer"
    explicit = str(playlist.get("description", "")).strip()
    if explicit:
        return f"{explicit} | {managed_tag}"

    name = str(playlist.get("name", "")).strip()
    vibe = f"Vibe: {name}" if name else "Vibe: curated from your liked songs"
    return f"{vibe} | {managed_tag}"


def make_ytmusic(auth_file: Path) -> YTMusic:
    session = requests.Session()
    session.request = functools.partial(session.request, timeout=90)
    return YTMusic(str(auth_file), requests_session=session)


def export_liked(yt: YTMusic, output_path: Path) -> list[dict[str, Any]]:
    songs = yt.get_liked_songs(limit=5000)
    tracks = []
    for t in songs.get("tracks", []):
        tracks.append(
            {
                "videoId": t.get("videoId"),
                "title": t.get("title", ""),
                "artists": [a.get("name", "") for a in t.get("artists", [])],
                "album": (t.get("album") or {}).get("name", ""),
                "duration": t.get("duration", ""),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tracks, ensure_ascii=False, indent=2), encoding="utf-8")
    return tracks


def export_new_likes(yt: YTMusic, state_path: Path, output_path: Path) -> list[dict[str, Any]]:
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"processed_video_ids": []}

    processed = set(state.get("processed_video_ids", []))
    songs = yt.get_liked_songs(limit=5000)
    tracks = []

    for t in songs.get("tracks", []):
        video_id = t.get("videoId")
        if not video_id or video_id in processed:
            continue
        tracks.append(
            {
                "videoId": video_id,
                "title": t.get("title", ""),
                "artists": [a.get("name", "") for a in t.get("artists", [])],
                "album": (t.get("album") or {}).get("name", ""),
                "duration": t.get("duration", ""),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tracks, ensure_ascii=False, indent=2), encoding="utf-8")
    return tracks


def initialize_state(liked_path: Path, state_path: Path) -> None:
    liked = json.loads(liked_path.read_text(encoding="utf-8"))
    ids = []
    seen = set()
    for track in liked:
        video_id = track.get("videoId")
        if video_id and video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)

    state_path.write_text(
        json.dumps({"processed_video_ids": ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_managed_playlists(plan_path: Path, managed_path: Path) -> list[str]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
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

    managed_path.write_text(
        json.dumps({"playlists": names}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return names


def delete_managed_playlists(yt: YTMusic, managed_path: Path) -> int:
    managed = json.loads(managed_path.read_text(encoding="utf-8")) if managed_path.exists() else {"playlists": []}
    managed_names = {normalize(name) for name in managed.get("playlists", [])}

    deleted = 0
    for playlist in yt.get_library_playlists(limit=500):
        title = (playlist.get("title") or "").strip()
        playlist_id = playlist.get("playlistId")
        if not title or not playlist_id:
            continue
        if normalize(title) in managed_names:
            yt.delete_playlist(playlist_id)
            deleted += 1

    return deleted


def _build_existing_playlist_map(yt: YTMusic) -> dict[str, dict[str, str]]:
    playlists = yt.get_library_playlists(limit=500)
    playlist_map = {}

    for p in playlists:
        name = (p.get("title") or "").strip()
        playlist_id = p.get("playlistId")
        if name and playlist_id:
            playlist_map[normalize(name)] = {"title": name, "playlistId": playlist_id}

    return playlist_map


def _existing_ids(yt: YTMusic, playlist_id: str) -> set[str]:
    try:
        playlist = yt.get_playlist(playlist_id, limit=5000)
    except Exception:
        return set()

    ids = set()
    for t in playlist.get("tracks", []):
        video_id = t.get("videoId")
        if video_id:
            ids.add(video_id)
    return ids


def apply_plan(
    yt: YTMusic,
    liked_path: Path,
    plan_path: Path,
    missing_path: Path,
    create_playlists: bool,
) -> dict[str, Any]:
    liked_tracks = json.loads(liked_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    existing = _build_existing_playlist_map(yt)
    missing_items: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []

    for playlist in plan.get("playlists", []):
        playlist_name = (playlist.get("name") or "").strip()
        if not playlist_name:
            continue

        normalized_name = normalize(playlist_name)
        if normalized_name in existing:
            playlist_id = existing[normalized_name]["playlistId"]
            existing_video_ids = _existing_ids(yt, playlist_id)
            action = "reused"
        elif create_playlists:
            playlist_id = yt.create_playlist(
                title=playlist_name,
                description=build_playlist_description(playlist),
            )
            existing[normalized_name] = {"title": playlist_name, "playlistId": playlist_id}
            existing_video_ids = set()
            action = "created"
        else:
            results.append({"name": playlist_name, "status": "missing-playlist", "added": 0})
            continue

        to_add: list[str] = []
        seen_ids = set()

        for song in playlist.get("songs", []):
            match, _match_type = find_match(song, liked_tracks)
            if not match:
                missing_items.append(
                    {
                        "playlist": playlist_name,
                        "title": song.get("title", ""),
                        "artist": song.get("artist", ""),
                    }
                )
                continue

            video_id = match.get("videoId")
            if not video_id:
                missing_items.append(
                    {
                        "playlist": playlist_name,
                        "title": song.get("title", ""),
                        "artist": song.get("artist", ""),
                    }
                )
                continue

            if video_id in seen_ids or video_id in existing_video_ids:
                continue

            seen_ids.add(video_id)
            to_add.append(video_id)

        if to_add:
            yt.add_playlist_items(playlist_id, to_add)

        results.append({"name": playlist_name, "status": action, "added": len(to_add)})

    missing_path.parent.mkdir(parents=True, exist_ok=True)
    missing_path.write_text(json.dumps(missing_items, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"results": results, "missing": len(missing_items)}


def apply_new_likes(
    yt: YTMusic,
    new_likes_path: Path,
    new_plan_path: Path,
    state_path: Path,
    missing_path: Path,
) -> dict[str, Any]:
    new_likes = json.loads(new_likes_path.read_text(encoding="utf-8"))
    plan = json.loads(new_plan_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"processed_video_ids": []}
    processed = set(state.get("processed_video_ids", []))

    playlist_map = _build_existing_playlist_map(yt)

    missing: list[dict[str, str]] = []
    matched_video_ids = set()
    results: list[dict[str, Any]] = []

    for playlist in plan.get("playlists", []):
        name = (playlist.get("name") or "").strip()
        if not name:
            continue

        normalized_name = normalize(name)
        playlist_info = playlist_map.get(normalized_name)
        if not playlist_info:
            results.append({"name": name, "status": "missing-playlist", "added": 0})
            continue

        playlist_id = playlist_info["playlistId"]
        existing_ids = _existing_ids(yt, playlist_id)
        to_add: list[str] = []
        seen_for_playlist = set()

        for song in playlist.get("songs", []):
            match, _match_type = find_match(song, new_likes)
            if not match:
                missing.append({"playlist": name, "title": song.get("title", ""), "artist": song.get("artist", "")})
                continue

            video_id = match.get("videoId")
            if not video_id:
                missing.append({"playlist": name, "title": song.get("title", ""), "artist": song.get("artist", "")})
                continue

            matched_video_ids.add(video_id)
            if video_id in seen_for_playlist or video_id in existing_ids:
                continue

            seen_for_playlist.add(video_id)
            to_add.append(video_id)

        if to_add:
            yt.add_playlist_items(playlist_id, to_add)

        results.append({"name": name, "status": "ok", "added": len(to_add)})

    processed.update(matched_video_ids)
    state_path.write_text(
        json.dumps({"processed_video_ids": sorted(processed)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    missing_path.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"results": results, "missing": len(missing), "processed": len(matched_video_ids)}


def preview_plan(liked_path: Path, plan_path: Path, missing_path: Path) -> dict[str, Any]:
    liked = json.loads(liked_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    total_matched = 0
    total_missing = 0
    total_loose = 0
    total_ambiguous = 0

    missing_items: list[dict[str, str]] = []

    for playlist in plan.get("playlists", []):
        for song in playlist.get("songs", []):
            match, match_type = find_match(song, liked)
            if not match:
                total_missing += 1
                missing_items.append(
                    {
                        "playlist": playlist.get("name", ""),
                        "title": song.get("title", ""),
                        "artist": song.get("artist", ""),
                    }
                )
            else:
                total_matched += 1
                if match_type == "loose":
                    total_loose += 1
                elif match_type == "ambiguous":
                    total_ambiguous += 1

    missing_path.parent.mkdir(parents=True, exist_ok=True)
    missing_path.write_text(json.dumps(missing_items, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "matched": total_matched,
        "missing": total_missing,
        "loose": total_loose,
        "ambiguous": total_ambiguous,
    }
