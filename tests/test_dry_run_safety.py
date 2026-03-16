import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.workflows import run_cleanup, run_full_reset, run_setup, run_weekly_sync


class _FakeYTReadOnly:
    def get_library_playlists(self, limit: int = 500):  # noqa: ARG002
        return [{"title": "Existing", "playlistId": "pl-1"}]

    def get_playlist(self, playlist_id: str, limit: int = 5000):  # noqa: ARG002
        return {"tracks": []}

    def get_liked_songs(self, limit: int = 5000):  # noqa: ARG002
        return {"tracks": []}


class DryRunSafetyTests(unittest.TestCase):
    def test_setup_dry_run_does_not_create_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "ws"
            auth = root / "auth.json"
            auth.write_text("{}", encoding="utf-8")

            with (
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=_FakeYTReadOnly()),
                patch(
                    "ytmusic_organizer.workflows.export_liked_data",
                    return_value=[{"videoId": "v1", "title": "Song", "artists": ["A"]}],
                ),
                patch(
                    "ytmusic_organizer.workflows._obtain_full_plan",
                    return_value={"playlists": [{"name": "Mix", "songs": []}]},
                ),
                patch(
                    "ytmusic_organizer.workflows.apply_plan",
                    side_effect=AssertionError("no apply in dry-run"),
                ),
                patch(
                    "ytmusic_organizer.workflows.update_managed_playlists",
                    side_effect=AssertionError("no managed writes in dry-run"),
                ),
                patch(
                    "ytmusic_organizer.workflows.initialize_state",
                    side_effect=AssertionError("no state init in dry-run"),
                ),
            ):
                result = run_setup(
                    workspace=workspace,
                    auth_file=str(auth),
                    mode="manual",
                    interactive=False,
                    dry_run=True,
                )

            self.assertFalse(workspace.exists())
            self.assertTrue(result["dry_run"])

    def test_cleanup_dry_run_keeps_local_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            managed = workspace / "managed_playlists.json"
            managed.write_text(
                json.dumps(
                    {"schema_version": 2, "playlists": [{"name": "Managed", "playlist_id": "pl-1"}]}
                ),
                encoding="utf-8",
            )
            state = workspace / "state.json"
            state.write_text("{}", encoding="utf-8")

            with patch(
                "ytmusic_organizer.workflows.delete_managed_playlists",
                side_effect=AssertionError("no remote delete in dry-run"),
            ):
                result = run_cleanup(workspace=workspace, local_only=True, dry_run=True)

            self.assertTrue(managed.exists())
            self.assertTrue(state.exists())
            self.assertTrue(result["dry_run"])
            self.assertTrue(result["local_only"])
            self.assertIn("would_remove_local_files", result)

    def test_rebuild_dry_run_does_not_run_mutating_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "config.toml").write_text(
                'auth_file = "browser.json"\nclassification_mode = "manual"\nopenai_model = "gpt-4.1-mini"\n',
                encoding="utf-8",
            )
            (workspace / "browser.json").write_text("{}", encoding="utf-8")

            with (
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=_FakeYTReadOnly()),
                patch(
                    "ytmusic_organizer.workflows.export_liked_data",
                    return_value=[{"videoId": "v1", "title": "Song", "artists": ["A"]}],
                ),
                patch(
                    "ytmusic_organizer.workflows._obtain_full_plan",
                    return_value={"playlists": [{"name": "Mix", "songs": []}]},
                ),
                patch(
                    "ytmusic_organizer.workflows.delete_managed_playlists",
                    side_effect=AssertionError("no delete in dry-run"),
                ),
                patch(
                    "ytmusic_organizer.workflows.apply_plan",
                    side_effect=AssertionError("no apply in dry-run"),
                ),
                patch(
                    "ytmusic_organizer.workflows.update_managed_playlists",
                    side_effect=AssertionError("no managed writes in dry-run"),
                ),
                patch(
                    "ytmusic_organizer.workflows.initialize_state",
                    side_effect=AssertionError("no state init in dry-run"),
                ),
            ):
                result = run_full_reset(
                    workspace=workspace,
                    mode="manual",
                    interactive=False,
                    dry_run=True,
                )

            self.assertTrue(result["dry_run"])
            self.assertIn("would_delete_playlists", result)

    def test_sync_dry_run_does_not_write_state_or_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            (workspace / "bootstrap.json").write_text(
                json.dumps({"completed": True}), encoding="utf-8"
            )
            (workspace / "config.toml").write_text(
                'auth_file = "browser.json"\nclassification_mode = "manual"\nopenai_model = "gpt-4.1-mini"\n',
                encoding="utf-8",
            )
            (workspace / "browser.json").write_text("{}", encoding="utf-8")
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": []}), encoding="utf-8"
            )

            with (
                patch("ytmusic_organizer.workflows.make_ytmusic", return_value=_FakeYTReadOnly()),
                patch(
                    "ytmusic_organizer.workflows.export_new_likes_data",
                    return_value=[{"videoId": "v1", "title": "Song", "artists": ["A"]}],
                ),
                patch(
                    "ytmusic_organizer.workflows._obtain_new_plan",
                    return_value={"playlists": [{"name": "Existing", "songs": []}]},
                ),
                patch(
                    "ytmusic_organizer.workflows.apply_new_likes",
                    side_effect=AssertionError("no apply in dry-run"),
                ),
            ):
                result = run_weekly_sync(
                    workspace=workspace,
                    mode="manual",
                    interactive=False,
                    dry_run=True,
                )

            self.assertTrue(result["dry_run"])
            self.assertEqual(result["new_likes"], 1)
            self.assertFalse((data_dir / "new_plan.json").exists())
            self.assertFalse((data_dir / "new_likes.json").exists())
            self.assertFalse((data_dir / "missing_matches.json").exists())


if __name__ == "__main__":
    unittest.main()
