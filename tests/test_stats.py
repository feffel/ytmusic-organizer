import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.workflows import run_stats


class StatsTests(unittest.TestCase):
    def test_run_stats_empty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 0)
            self.assertEqual(result["managed_playlists"], 0)
            self.assertEqual(result["missing_matches"], 0)
            self.assertEqual(result["new_likes_pending"], 0)
            self.assertEqual(result["liked_snapshot_count"], 0)
            self.assertFalse(result["artifact_presence"]["state"])

    def test_run_stats_partial_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir(parents=True)
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["a", "b"]}),
                encoding="utf-8",
            )
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 2)
            self.assertEqual(result["managed_playlists"], 0)
            self.assertTrue(result["artifact_presence"]["state"])
            self.assertFalse(result["artifact_presence"]["managed_playlists"])

    def test_run_stats_populated_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True)
            (workspace / "state.json").write_text(
                json.dumps({"processed_video_ids": ["a", "b", "c"]}),
                encoding="utf-8",
            )
            (workspace / "managed_playlists.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "playlists": [
                            {"name": "A", "playlist_id": "1"},
                            {"name": "B", "playlist_id": "2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (data_dir / "missing_matches.json").write_text(json.dumps([{"song": "x"}]), encoding="utf-8")
            (data_dir / "new_likes.json").write_text(json.dumps([{"video_id": "n1"}]), encoding="utf-8")
            (data_dir / "liked_songs.json").write_text(
                json.dumps([{"video_id": "a"}, {"video_id": "b"}]),
                encoding="utf-8",
            )
            result = run_stats(workspace)
            self.assertEqual(result["processed_likes"], 3)
            self.assertEqual(result["managed_playlists"], 2)
            self.assertEqual(result["missing_matches"], 1)
            self.assertEqual(result["new_likes_pending"], 1)
            self.assertEqual(result["liked_snapshot_count"], 2)

    def test_cli_stats_json_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "stats",
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "stats")
            self.assertIn("processed_likes", payload["result"])
            self.assertIn("artifact_presence", payload["result"])


if __name__ == "__main__":
    unittest.main()
