from typing import Any


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _validate_song(song: Any, label: str) -> None:
    song = _require_dict(song, label)
    _require_str(song.get("title"), f"{label}.title")
    _require_str(song.get("artist"), f"{label}.artist")


def _validate_playlists(plan: dict[str, Any]) -> None:
    playlists = plan.get("playlists")
    if not isinstance(playlists, list):
        raise ValueError("playlists must be an array")

    for pidx, playlist in enumerate(playlists):
        playlist = _require_dict(playlist, f"playlists[{pidx}]")
        _require_str(playlist.get("name"), f"playlists[{pidx}].name")
        description = playlist.get("description")
        if description is not None and (
            not isinstance(description, str) or not description.strip()
        ):
            raise ValueError(
                f"playlists[{pidx}].description must be a non-empty string when provided"
            )
        songs = playlist.get("songs")
        if not isinstance(songs, list):
            raise ValueError(f"playlists[{pidx}].songs must be an array")
        for sidx, song in enumerate(songs):
            _validate_song(song, f"playlists[{pidx}].songs[{sidx}]")


def validate_full_plan(plan: Any) -> dict[str, Any]:
    plan = _require_dict(plan, "plan")

    strategy_options = plan.get("strategy_options")
    if strategy_options is not None:
        if not isinstance(strategy_options, list):
            raise ValueError("strategy_options must be an array")
        for idx, item in enumerate(strategy_options):
            item = _require_dict(item, f"strategy_options[{idx}]")
            _require_str(item.get("name"), f"strategy_options[{idx}].name")
            _require_str(item.get("description"), f"strategy_options[{idx}].description")

    recommended = plan.get("recommended_strategy")
    if recommended is not None:
        _require_str(recommended, "recommended_strategy")

    _validate_playlists(plan)
    return plan


def validate_new_plan(plan: Any) -> dict[str, Any]:
    plan = _require_dict(plan, "plan")
    _validate_playlists(plan)
    return plan
