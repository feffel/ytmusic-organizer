import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from ytmusic_organizer.workflows import cleanup_local_artifacts, run_cleanup


class CleanupTests(unittest.TestCase):
    def test_cleanup_local_artifacts_removes_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [
                root / "state.json",
                root / "managed_playlists.json",
                root / "bootstrap.json",
                root / "setup_state.json",
                root / "data" / "liked_songs.json",
                root / "data" / "new_likes.json",
            ]
            for f in files:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("{}", encoding="utf-8")

            removed = cleanup_local_artifacts(root)
            self.assertGreaterEqual(removed, len(files))
            for f in files:
                self.assertFalse(f.exists())

    def test_cleanup_removes_local_artifacts_even_when_auth_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True, exist_ok=True)
            (workspace / "config.toml").write_text(
                'auth_file = "browser.json"\nclassification_mode = "manual"\nopenai_model = "gpt-4.1-mini"\n',
                encoding="utf-8",
            )
            (workspace / "state.json").write_text("{}", encoding="utf-8")
            (workspace / "managed_playlists.json").write_text(
                '{"schema_version": 2, "playlists": []}',
                encoding="utf-8",
            )
            (workspace / "data").mkdir(parents=True, exist_ok=True)
            (workspace / "data" / "liked_songs.json").write_text("[]", encoding="utf-8")

            with patch(
                "ytmusic_organizer.workflows.delete_managed_playlists",
                side_effect=AssertionError("remote delete should be skipped"),
            ):
                result = run_cleanup(workspace=workspace, local_only=False, dry_run=False)

            self.assertEqual(result["deleted_playlists"], 0)
            self.assertGreaterEqual(result["removed_local_files"], 3)
            self.assertIn("remote_delete_error", result)
            self.assertIn("Auth file not found", result["remote_delete_error"])
            self.assertFalse((workspace / "state.json").exists())
            self.assertFalse((workspace / "managed_playlists.json").exists())


if __name__ == "__main__":
    unittest.main()
