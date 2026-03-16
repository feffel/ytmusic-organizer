import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.workflows import run_full_reset
from ytmusic_organizer.ytmusic_ops import delete_managed_playlists


class _FakeYT:
    def __init__(self, playlists: list[dict[str, str]]):
        self._playlists = playlists
        self.deleted: list[str] = []

    def get_library_playlists(self, limit: int = 500):  # noqa: ARG002
        return self._playlists

    def delete_playlist(self, playlist_id: str) -> None:
        self.deleted.append(playlist_id)


class DeletionSafetyTests(unittest.TestCase):
    def test_delete_managed_playlists_uses_ids_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            managed = Path(tmp) / "managed_playlists.json"
            managed.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "playlists": [
                            {"name": "Managed One", "playlist_id": "pl-1"},
                            {"name": "Managed Two", "playlist_id": "pl-2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            yt = _FakeYT(
                [
                    {"title": "Some Other Name", "playlistId": "pl-2"},
                    {"title": "Managed One", "playlistId": "different-id"},
                ]
            )
            result = delete_managed_playlists(yt, managed)

            self.assertEqual(result["deleted"], 1)
            self.assertEqual(yt.deleted, ["pl-2"])
            self.assertEqual(result["skipped_legacy"], [])

    def test_delete_managed_playlists_skips_legacy_name_only_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            managed = Path(tmp) / "managed_playlists.json"
            managed.write_text(json.dumps({"playlists": ["Managed One"]}), encoding="utf-8")

            yt = _FakeYT([{"title": "Managed One", "playlistId": "pl-1"}])
            result = delete_managed_playlists(yt, managed)

            self.assertEqual(result["deleted"], 0)
            self.assertEqual(yt.deleted, [])
            self.assertEqual(result["skipped_legacy"], ["Managed One"])


class FullResetSafetyTests(unittest.TestCase):
    def test_full_reset_deletes_using_previous_managed_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "config.toml").write_text(
                'auth_file = "browser.json"\nclassification_mode = "manual"\nopenai_model = "gpt-4.1-mini"\n',
                encoding="utf-8",
            )
            (workspace / "browser.json").write_text("{}", encoding="utf-8")
            (workspace / "managed_playlists.json").write_text(
                json.dumps(
                    {"schema_version": 2, "playlists": [{"name": "Old", "playlist_id": "old-id"}]}
                ),
                encoding="utf-8",
            )

            observed: dict[str, object] = {}

            def fake_obtain_full_plan(mode, config, paths, ui=None, **kwargs):  # noqa: ANN001,ARG001
                paths.playlist_plan.parent.mkdir(parents=True, exist_ok=True)
                paths.playlist_plan.write_text(
                    json.dumps({"playlists": [{"name": "New", "songs": []}]}),
                    encoding="utf-8",
                )
                return {"playlists": [{"name": "New", "songs": []}]}

            def fake_delete(yt, managed_path):  # noqa: ANN001
                data = json.loads(Path(managed_path).read_text(encoding="utf-8"))
                observed["managed_at_delete"] = data
                return {"deleted": 1, "skipped_legacy": []}

            def fake_apply_plan(*args, **kwargs):  # noqa: ANN002,ANN003
                return {
                    "results": [
                        {"name": "New", "status": "created", "added": 0, "playlist_id": "new-id"}
                    ],
                    "missing": 0,
                }

            with (
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=object()),
                patch("ytmusic_organizer.workflows.export_liked", return_value=[]),
                patch(
                    "ytmusic_organizer.workflows._obtain_full_plan",
                    side_effect=fake_obtain_full_plan,
                ),
                patch(
                    "ytmusic_organizer.workflows.delete_managed_playlists", side_effect=fake_delete
                ),
                patch("ytmusic_organizer.workflows.apply_plan", side_effect=fake_apply_plan),
                patch("ytmusic_organizer.workflows.initialize_state", return_value=None),
            ):
                run_full_reset(workspace=workspace, mode="manual")

            self.assertEqual(
                observed["managed_at_delete"],
                {"schema_version": 2, "playlists": [{"name": "Old", "playlist_id": "old-id"}]},
            )
            final_managed = json.loads(
                (workspace / "managed_playlists.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                final_managed,
                {"schema_version": 2, "playlists": [{"name": "New", "playlist_id": "new-id"}]},
            )


if __name__ == "__main__":
    unittest.main()
