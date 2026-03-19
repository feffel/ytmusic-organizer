from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.ytmusic_ops import (
    _build_existing_playlist_map,
    _existing_ids,
    apply_new_likes,
    delete_managed_playlists,
    export_liked_data,
    export_new_likes,
    export_new_likes_data,
)


class _FakeYTWithLimits:
    def __init__(self) -> None:
        self.liked_limits: list[int | None] = []
        self.library_limits: list[int | None] = []
        self.playlist_limits: list[int | None] = []

    def get_liked_songs(self, limit: int | None = 100):  # noqa: ANN001
        self.liked_limits.append(limit)
        return {"tracks": []}

    def get_library_playlists(self, limit: int | None = 25):  # noqa: ANN001
        self.library_limits.append(limit)
        return []

    def get_playlist(self, playlist_id: str, limit: int | None = 100):  # noqa: ANN001,ARG002
        self.playlist_limits.append(limit)
        return {"tracks": []}

    def delete_playlist(self, playlist_id: str) -> None:  # noqa: ARG002
        return

    def add_playlist_items(self, playlist_id: str, items: list[str]) -> None:  # noqa: ARG002
        return


class ReliabilityHardeningTests(unittest.TestCase):
    def test_export_uses_unbounded_liked_songs_fetch(self) -> None:
        yt = _FakeYTWithLimits()
        export_liked_data(yt)
        export_new_likes_data(yt, processed_video_ids=set())
        self.assertEqual(yt.liked_limits, [None, None])

    def test_playlist_lookups_use_unbounded_library_fetch(self) -> None:
        yt = _FakeYTWithLimits()
        with tempfile.TemporaryDirectory() as tmp:
            managed = Path(tmp) / "managed_playlists.json"
            managed.write_text(
                json.dumps(
                    {"schema_version": 2, "playlists": [{"name": "A", "playlist_id": "pl-1"}]}
                ),
                encoding="utf-8",
            )
            delete_managed_playlists(yt, managed)
        _build_existing_playlist_map(yt)
        self.assertEqual(yt.library_limits, [None, None])

    def test_existing_playlist_track_fetch_is_unbounded(self) -> None:
        yt = _FakeYTWithLimits()
        _existing_ids(yt, "pl-1")
        self.assertEqual(yt.playlist_limits, [None])

    def test_export_new_likes_tolerates_corrupt_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state.json"
            out = root / "data" / "new_likes.json"
            state.write_text("{invalid", encoding="utf-8")
            yt = _FakeYTWithLimits()
            result = export_new_likes(yt, state, out)
            self.assertEqual(result, [])
            self.assertTrue(out.exists())

    def test_apply_new_likes_tolerates_corrupt_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state.json"
            new_likes = root / "data" / "new_likes.json"
            new_plan = root / "data" / "new_plan.json"
            missing = root / "data" / "missing_matches.json"
            new_likes.parent.mkdir(parents=True, exist_ok=True)
            state.write_text("{invalid", encoding="utf-8")
            new_likes.write_text("[]", encoding="utf-8")
            new_plan.write_text('{"playlists": []}', encoding="utf-8")
            yt = _FakeYTWithLimits()
            result = apply_new_likes(yt, new_likes, new_plan, state, missing)
            self.assertEqual(result["processed"], 0)
            written = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(written, {"processed_video_ids": []})


if __name__ == "__main__":
    unittest.main()
