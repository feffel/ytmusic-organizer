import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


class CliJsonOutputTests(unittest.TestCase):
    def test_cleanup_local_only_json_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "cleanup",
                    "--workspace",
                    str(workspace),
                    "--local-only",
                    "--yes",
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["command"], "cleanup")
            self.assertIn("removed_local_files", payload["result"])

    def test_setup_json_error_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            missing_auth = Path(tmp) / "missing-browser.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--non-interactive",
                    "--auth-file",
                    str(missing_auth),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "setup")
            self.assertIn("Auth file is missing", payload["error"])

    def test_preview_missing_default_plan_returns_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "preview",
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "preview")
            self.assertIn("Preview prerequisites are missing", payload["error"])
            self.assertIn("Plan file not found", payload["error"])
            self.assertIn("ytmo setup", payload["error"])

    def test_preview_missing_liked_snapshot_returns_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            plan_path = data_dir / "custom-plan.json"
            plan_path.write_text(
                json.dumps(
                    {"playlists": [{"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}]}
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "preview",
                    "--workspace",
                    str(workspace),
                    "--plan",
                    str(plan_path),
                    "--json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout.strip())
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "preview")
            self.assertIn("Preview prerequisites are missing", payload["error"])
            self.assertIn("Liked songs snapshot not found", payload["error"])
            self.assertIn("ytmo setup", payload["error"])

    def test_preview_success_writes_missing_matches_and_returns_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            data_dir = workspace / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            liked_path = data_dir / "liked_songs.json"
            liked_path.write_text(
                json.dumps(
                    [
                        {
                            "videoId": "vid-1",
                            "title": "Song A",
                            "artists": ["Artist A"],
                            "album": "",
                            "duration": "",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            plan_path = data_dir / "playlist_plan.json"
            plan_path.write_text(
                json.dumps(
                    {"playlists": [{"name": "Chill", "songs": [{"title": "Song A", "artist": "Artist A"}]}]}
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ytmusic_organizer.cli",
                    "preview",
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
            self.assertEqual(payload["command"], "preview")
            self.assertEqual(payload["result"]["matched"], 1)
            self.assertEqual(payload["result"]["missing"], 0)
            self.assertEqual(payload["result"]["loose"], 0)
            self.assertEqual(payload["result"]["ambiguous"], 0)

            missing_matches = data_dir / "missing_matches.json"
            self.assertTrue(missing_matches.exists())
            self.assertEqual(json.loads(missing_matches.read_text(encoding="utf-8")), [])


if __name__ == "__main__":
    unittest.main()
